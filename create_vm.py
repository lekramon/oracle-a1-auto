#!/usr/bin/env python3
"""Tenta criar uma única OCI A1.Flex Always Free, preferindo 2 OCPU/12 GB e usando 1 OCPU/6 GB como fallback.

Executado por GitHub Actions a cada 5 minutos. Em falta de capacidade, sai
normalmente e tenta no próximo agendamento. Falhas de configuração não são
silenciadas. Nunca seleciona shapes ou sistemas com licença pagos.
"""

import hashlib
import os
import sys
import time

import oci


SHAPE = "VM.Standard.A1.Flex"
REGION = "sa-saopaulo-1"
INSTANCE_NAME = "hermes-agent"
PRIMARY = (2, 12)
FALLBACK = (1, 6)
BOOT_GB = 50


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Secret ausente: {name}")
    return value


def report_status(status: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"status={status}\n")
    print(f"RESULTADO: {status}", flush=True)


def capacity_error(exc: oci.exceptions.ServiceError) -> bool:
    code = (exc.code or "").lower()
    msg = (exc.message or "").lower()
    return (
        code in {"outofhostcapacity", "outofcapacity"}
        or ("capacity" in msg and ("out of" in msg or "insufficient" in msg))
    )


def main() -> None:
    compartment = required("OCI_COMPARTMENT_OCID")
    subnet = required("OCI_SUBNET_OCID")
    ssh_public_key = required("OCI_SSH_PUBLIC_KEY")
    if not ssh_public_key.startswith(("ssh-rsa ", "ssh-ed25519 ", "ecdsa-sha2-")):
        raise RuntimeError("OCI_SSH_PUBLIC_KEY deve conter a linha da chave PUBLICA SSH, nao a privada")

    config = {
        "user": required("OCI_USER_OCID"),
        "tenancy": required("OCI_TENANCY_OCID"),
        "fingerprint": required("OCI_FINGERPRINT"),
        "key_content": required("OCI_PRIVATE_KEY").replace("\\n", "\n") + "\n",
        "region": REGION,
    }
    oci.config.validate_config(config)
    compute = oci.core.ComputeClient(config)
    identity = oci.identity.IdentityClient(config)

    # Não recrie uma A1 já existente no compartimento. Isso evita gastos,
    # duplicação e consumo involuntário da franquia de 2 OCPUs/12 GB.
    instances = oci.pagination.list_call_get_all_results(
        compute.list_instances, compartment_id=compartment
    ).data
    existing = [
        i for i in instances
        if i.shape == SHAPE
        and i.lifecycle_state not in {"TERMINATED", "TERMINATING"}
        # A launch can briefly be PROVISIONING/STARTING; it still counts and
        # must prevent a second request in a later scheduled run.
    ]
    if existing:
        print(f"A1 ja existe no compartimento: {existing[0].display_name} ({existing[0].lifecycle_state}).")
        report_status("already_exists")
        return

    # Busca a versão estável mais recente de Ubuntu 26.04 compativel com A1.
    images = oci.pagination.list_call_get_all_results(
        compute.list_images,
        compartment_id=compartment,
        operating_system="Canonical Ubuntu",
        operating_system_version="26.04",
        shape=SHAPE,
        sort_by="TIMECREATED",
        sort_order="DESC",
    ).data
    candidates = [
        im for im in images
        if "minimal" not in (im.display_name or "").lower()
        and "26.04" in (im.display_name or "")
        and im.lifecycle_state == "AVAILABLE"
    ]
    if not candidates:
        raise RuntimeError("Imagem Ubuntu 26.04 full para A1.Flex nao encontrada na regiao Sao Paulo")
    image = candidates[0]
    print(f"Imagem escolhida: {image.display_name}")

    ads = identity.list_availability_domains(compartment_id=compartment).data
    if not ads:
        raise RuntimeError("Nenhum Availability Domain listado para o compartimento")

    # Esgota a configuração preferida em todos os ADs antes do fallback.
    for ocpus, ram_gb, label in [
        (PRIMARY[0], PRIMARY[1], "preferida"),
        (FALLBACK[0], FALLBACK[1], "fallback"),
    ]:
        for ad in ads:
            print(
                f"Tentando {SHAPE} / {ocpus} OCPU / {ram_gb} GB "
                f"({label}) em {ad.name}",
                flush=True,
            )
            details = oci.core.models.LaunchInstanceDetails(
                availability_domain=ad.name,
                compartment_id=compartment,
                display_name=INSTANCE_NAME,
                shape=SHAPE,
                shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=ocpus,
                    memory_in_gbs=ram_gb,
                ),
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image",
                    image_id=image.id,
                    boot_volume_size_in_gbs=BOOT_GB,
                ),
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet,
                    assign_public_ip=True,
                ),
                metadata={"ssh_authorized_keys": ssh_public_key},
                freeform_tags={
                    "automation": "oracle-a1-claim",
                    "purpose": "hermes",
                    "profile": f"{ocpus}ocpu-{ram_gb}gb",
                },
            )

            # Token por janela de 5 minutos e configuração.
            bucket = int(time.time() // 300)
            token = hashlib.sha256(
                f"{compartment}:{subnet}:{INSTANCE_NAME}:{ad.name}:{ocpus}:{ram_gb}:{bucket}".encode()
            ).hexdigest()[:48]
            try:
                created = compute.launch_instance(details, opc_retry_token=token).data
            except oci.exceptions.ServiceError as exc:
                if capacity_error(exc):
                    print(
                        f"Sem capacidade para {ocpus} OCPU/{ram_gb} GB em {ad.name}.",
                        flush=True,
                    )
                    continue
                print(
                    f"Erro OCI: HTTP {exc.status}, codigo {exc.code}: {exc.message}",
                    file=sys.stderr,
                )
                raise

            print(f"INSTANCIA SOLICITADA! OCID: {created.id}")
            print(f"Estado inicial: {created.lifecycle_state}. Confira o status no painel OCI.")
            report_status("created")
            return

    report_status("unavailable")


if __name__ == "__main__":
    main()

