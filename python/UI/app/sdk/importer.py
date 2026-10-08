from pathlib import Path
import re

from app.sdk.manager import SDKManager


class KeyImporter:

    def __init__(self):
        self.sdk = SDKManager()

    def scan_folder(self, folder):

        folder = Path(folder).expanduser()

        if not folder.exists():
            raise FileNotFoundError(folder)

        devices = {}

        # Accept both the SDK's original *_public.pem form and the
        # *_public_key.pem form commonly used alongside *_private_key.pem.
        public_pattern = re.compile(r"(.+)_v(\d+)_public(?:_key)?\.pem$")
        private_pattern = re.compile(r"(.+)_v(\d+)_private_key\.pem$")

        for pem in folder.glob("*.pem"):

            name = pem.name

            m = public_pattern.match(name)

            if m:

                device = m.group(1)
                version = int(m.group(2))

                devices.setdefault(device, {})
                devices[device].setdefault(version, {})
                devices[device][version]["public"] = pem

                continue

            m = private_pattern.match(name)

            if m:

                device = m.group(1)
                version = int(m.group(2))

                devices.setdefault(device, {})
                devices[device].setdefault(version, {})
                devices[device][version]["private"] = pem

        return devices

    def import_folder(self, folder):

        devices = self.scan_folder(folder)

        imported = []
        skipped = []
        failed = []

        for device in sorted(devices.keys()):

            versions = devices[device]

            for version in sorted(versions.keys()):

                pair = versions[version]

                if "public" not in pair or "private" not in pair:

                    skipped.append(
                        {
                            "device": device,
                            "version": version,
                            "reason": "Missing public/private key",
                        }
                    )
                    continue

                code, out, err = self.sdk.import_key(
                    customer_id=device,
                    version=version,
                    public_key=pair["public"],
                    private_key=pair["private"],
                )

                text = (out + err).strip()

                if code == 0:

                    imported.append(
                        {
                            "device": device,
                            "version": version,
                            "message": text,
                        }
                    )

                else:

                    # Treat already-imported as skipped, not failed.
                    if "ERR_CUSTOMER_ALREADY_EXISTS" in text:

                        skipped.append(
                            {
                                "device": device,
                                "version": version,
                                "reason": "Already imported",
                            }
                        )

                    else:

                        failed.append(
                            {
                                "device": device,
                                "version": version,
                                "reason": text,
                            }
                        )

        return {
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
        }


if __name__ == "__main__":

    folder = input("Keys folder: ").strip()

    importer = KeyImporter()

    result = importer.import_folder(folder)

    print("\n========== IMPORT SUMMARY ==========\n")

    for item in result["imported"]:
        print(f"✓ {item['device']} v{item['version']}")

    for item in result["skipped"]:
        print(f"- {item['device']} v{item['version']} ({item['reason']})")

    for item in result["failed"]:
        print(f"✗ {item['device']} v{item['version']}")
        print(item["reason"])

    print("\n----------------------------------")
    print("Imported :", len(result["imported"]))
    print("Skipped  :", len(result["skipped"]))
    print("Failed   :", len(result["failed"]))
