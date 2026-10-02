import re
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QGroupBox,
)

from app.sdk.manager import SDKManager
from app.sdk.importer import KeyImporter
from app.utils.settings import Settings
from app.utils.logger import Logger


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.sdk = SDKManager()
        self.importer = KeyImporter()
        self.settings = Settings()
        self.logger = Logger()

        self.setWindowTitle("Robocap Decryptor")
        self.resize(900, 650)

        self.build_ui()

        self.load_settings()

        self.refresh_status()

    def validate_output(self):
        input_text = self.inputEdit.text().strip()
        output_text = self.outputEdit.text().strip()
        if not input_text or not output_text:
            return None
        input_path = Path(input_text).expanduser().resolve()
        output_path = Path(output_text).expanduser().resolve()
        if output_path == input_path or input_path in output_path.parents:
            return ("The output folder must be outside the input folder. Select a "
                    "separate folder, such as Downloads/output.")
        return None

    def build_ui(self):

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)

        #
        # SDK STATUS
        #

        status = QGroupBox("SDK Status")

        s = QVBoxLayout(status)

        self.sdkLabel = QLabel()

        self.vaultLabel = QLabel()

        self.bulkLabel = QLabel()

        s.addWidget(self.sdkLabel)

        s.addWidget(self.vaultLabel)

        s.addWidget(self.bulkLabel)

        layout.addWidget(status)

        #
        # KEYS
        #

        keys = QGroupBox("Keys Folder")

        k = QHBoxLayout(keys)

        self.keysEdit = QLineEdit()

        browse = QPushButton("Browse")

        browse.clicked.connect(self.pick_keys)

        self.importButton = QPushButton("Import Keys")

        self.importButton.clicked.connect(self.import_keys)

        k.addWidget(self.keysEdit)

        k.addWidget(browse)

        k.addWidget(self.importButton)

        layout.addWidget(keys)

        #
        # INPUT
        #

        inp = QGroupBox("Input")

        i = QHBoxLayout(inp)

        self.inputEdit = QLineEdit()

        browse = QPushButton("Browse")

        browse.clicked.connect(self.pick_input)

        i.addWidget(self.inputEdit)

        i.addWidget(browse)

        layout.addWidget(inp)

        #
        # OUTPUT
        #

        out = QGroupBox("Output")

        o = QHBoxLayout(out)

        self.outputEdit = QLineEdit()

        browse = QPushButton("Browse")

        browse.clicked.connect(self.pick_output)

        o.addWidget(self.outputEdit)

        o.addWidget(browse)

        layout.addWidget(out)

        #
        # WORKERS
        #

        row = QHBoxLayout()

        row.addWidget(QLabel("Workers"))

        self.workers = QSpinBox()

        self.workers.setRange(1, 32)

        self.workers.setValue(8)

        row.addWidget(self.workers)

        row.addStretch()

        layout.addLayout(row)

        #
        # DECRYPT
        #

        self.decryptButton = QPushButton("Start Decryption")

        self.decryptButton.clicked.connect(self.decrypt)

        layout.addWidget(self.decryptButton)

        #
        # PROGRESS
        #

        self.progress = QProgressBar()

        self.progress.setValue(0)

        layout.addWidget(self.progress)

        #
        # LOG
        #

        self.log = QTextEdit()

        self.log.setReadOnly(True)

        layout.addWidget(self.log)
    def refresh_status(self):

        self.sdkLabel.setText(
            "SDK: Found" if self.sdk.sdk_exists()
            else "SDK: Missing"
        )

        self.vaultLabel.setText(
            "Vault: Ready" if self.sdk.vault_exists()
            else "Vault: Missing"
        )

        self.bulkLabel.setText("Bulk Script: Found" if self.sdk.bulk_script_exists()
                               else "Bulk Script: Missing")

    def pick_keys(self):

        folder = QFileDialog.getExistingDirectory(self, "Keys Folder")

        if folder:
            self.keysEdit.setText(folder)
            self.settings.set("keys", folder)
            self.refresh_status()

    def pick_input(self):

        folder = QFileDialog.getExistingDirectory(self, "Input Folder")

        if folder:
            self.inputEdit.setText(folder)
            self.settings.set("input", folder)

    def pick_output(self):

        folder = QFileDialog.getExistingDirectory(self, "Output Folder")

        if folder:
            self.outputEdit.setText(folder)
            self.settings.set("output", folder)

    def load_settings(self):

        self.keysEdit.setText(self.settings.get("keys", ""))

        self.inputEdit.setText(self.settings.get("input", ""))

        self.outputEdit.setText(self.settings.get("output", ""))

        self.workers.setValue(max(1, min(32, int(self.settings.get("workers", 8)))))
        self.workers.valueChanged.connect(lambda value: self.settings.set("workers", value))

    def write_log(self, text):
        self.log.append(text)
        self.logger.info(text)

    def import_keys(self):

        folder = self.keysEdit.text().strip()

        if not folder:

            QMessageBox.warning(
                self,
                "Error",
                "Select a keys folder."
            )
            return

        self.write_log("Scanning keys...")

        try:
            result = self.importer.import_folder(folder)
        except Exception as exc:
            self.write_log(f"Key import failed: {exc}")
            QMessageBox.critical(self, "Import failed", str(exc))
            return

        for item in result["imported"]:

            self.write_log(
                f"✓ Imported {item['device']} v{item['version']}"
            )

        for item in result["skipped"]:

            self.write_log(
                f"- Skipped {item['device']} v{item['version']} ({item['reason']})"
            )

        for item in result["failed"]:

            self.write_log(
                f"✗ Failed {item['device']} v{item['version']}"
            )

            self.write_log(item["reason"])

        QMessageBox.information(
            self,
            "Finished",
            f"Imported: {len(result['imported'])}\n"
            f"Skipped: {len(result['skipped'])}\n"
            f"Failed: {len(result['failed'])}"
        )

        self.refresh_status()

    def decrypt(self):

        input_path = self.inputEdit.text().strip()

        output_path = self.outputEdit.text().strip()

        if not input_path or not output_path:

            QMessageBox.warning(
                self,
                "Error",
                "Select input and output folders."
            )
            return

        issue = self.validate_output()
        if issue:
            QMessageBox.warning(self, "Invalid output folder", issue)
            return

        if not Path(input_path).expanduser().is_dir():
            QMessageBox.warning(self, "Invalid input folder", "Select an existing input folder.")
            return

        if not self.sdk.vault_exists():
            QMessageBox.warning(self, "Keys not imported", "Import RSA key pairs before decrypting.")
            return

        self.progress.setValue(0)
        self.write_log("Starting bulk decrypt...")
        self.decryptButton.setEnabled(False)
        self.progress.setRange(0, 0)
        self._decrypt_thread = QThread(self)
        self._decrypt_worker = DecryptWorker(
            self.sdk, input_path, output_path, self.workers.value()
        )
        self._decrypt_worker.moveToThread(self._decrypt_thread)
        self._decrypt_thread.started.connect(self._decrypt_worker.run)
        self._decrypt_worker.line.connect(self.on_decrypt_line)
        self._decrypt_worker.finished.connect(self.on_decrypt_finished)
        self._decrypt_worker.finished.connect(self._decrypt_thread.quit)
        self._decrypt_thread.finished.connect(self._decrypt_worker.deleteLater)
        self._decrypt_thread.finished.connect(self._decrypt_thread.deleteLater)
        self._decrypt_thread.start()

    def on_decrypt_line(self, line):
        self.write_log(line)
        match = re.search(r"\b(\d+)/(\d+)\b", line)
        if match and int(match.group(2)):
            self.progress.setRange(0, 100)
            self.progress.setValue(min(99, int(100 * int(match.group(1)) / int(match.group(2)))))

    def on_decrypt_finished(self, code):
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if code == 0 else 0)
        self.decryptButton.setEnabled(True)
        if code == 0:
            QMessageBox.information(self, "Decryption complete", "Bulk decryption finished successfully.")
        else:
            QMessageBox.critical(self, "Decryption failed", f"Bulk decryption exited with code {code}. See the log for details.")


class DecryptWorker(QObject):
    line = Signal(str)
    finished = Signal(int)

    def __init__(self, sdk, input_path, output_path, workers):
        super().__init__()
        self.sdk = sdk
        self.input_path = input_path
        self.output_path = output_path
        self.workers = workers

    def run(self):
        code = 0
        try:
            for line in self.sdk.bulk_decrypt(
                self.input_path, self.output_path, self.workers
            ):
                if line.startswith("Process exited with code "):
                    code = int(line.rsplit(" ", 1)[-1])
                self.line.emit(line)
        except Exception as exc:
            self.line.emit(f"Bulk decrypt failed: {exc}")
            code = 1
        self.finished.emit(code)
