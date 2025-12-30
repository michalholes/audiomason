INSTALLATION – SYSTEM-WIDE (READ-ONLY)

AudioMason can be installed system-wide in a read-only manner.
This is intended for stable systems where AudioMason is used
as an explicit administrative tool.

There is no daemon, service, or background component.


REQUIREMENTS

- Linux system
- Python 3.11+
- ffmpeg available system-wide
- root access for installation


INSTALL DEPENDENCIES (Debian / Ubuntu)

sudo apt update
sudo apt install -y   python3   python3-venv   ffmpeg   unzip   rsync   p7zip-full   unrar-free


INSTALL LOCATION

Recommended layout:

/opt/audiomason/        application code (read-only)
/opt/audiomason/venv/   virtual environment
/usr/local/bin/audiomason  launcher symlink


INSTALL STEPS

1. Clone repository:

sudo mkdir -p /opt
sudo git clone https://github.com/michalholes/audiomason.git /opt/audiomason
cd /opt/audiomason

2. Create virtual environment:

sudo python3 -m venv /opt/audiomason/venv

3. Install AudioMason:

sudo /opt/audiomason/venv/bin/pip install -e .

4. Create launcher symlink:

sudo ln -sf /opt/audiomason/venv/bin/audiomason /usr/local/bin/audiomason


VERIFY INSTALLATION

audiomason --help
audiomason --dry-run --yes


CONFIGURATION FILES

System configuration:

/etc/audiomason/config.yaml

User configuration:

~/.config/audiomason/config.yaml


UPGRADING

cd /opt/audiomason
sudo git pull
sudo /opt/audiomason/venv/bin/pip install -e .


UNINSTALL

sudo rm -rf /opt/audiomason
sudo rm -f /usr/local/bin/audiomason


SECURITY NOTES

- Application code is read-only for normal users
- No background processes are installed
- Execution is always explicit
- Configuration is external to the application tree


DESIGN NOTE

AudioMason is intentionally boring, predictable, and safe.
That is a feature.
