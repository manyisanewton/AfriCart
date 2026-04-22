def build_image_job_payload(*, image_url: str, transforms: list[str] | None = None) -> dict:
    return {
        "image_url": image_url,
        "transforms": transforms or [],
    }
