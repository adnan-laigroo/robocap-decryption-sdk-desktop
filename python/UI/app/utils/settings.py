import json
from pathlib import Path


class Settings:

    def __init__(self):

        self.config_dir = Path.home() / ".robocap_decryptor"

        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "settings.json"

        self.data = {}

        self.load()

    def load(self):

        if self.config_file.exists():

            try:

                self.data = json.loads(
                    self.config_file.read_text()
                )

            except Exception:

                self.data = {}

        else:

            self.data = {}

            self.save()

    def save(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file.write_text(
            json.dumps(
                self.data,
                indent=4,
            )
        )

    def get(self, key, default=None):

        return self.data.get(key, default)

    def set(self, key, value):

        self.data[key] = value

        self.save()

    def clear(self):

        self.data = {}

        self.save()
