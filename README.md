# SecureDrop

SecureDrop is a command-line peer-to-peer file transfer application that lets users securely send files to contacts on the same local network. It prioritizes security at every layer — from account registration through file delivery — using industry-standard encryption, hashed credentials, and email-based identity verification.

---

## How It Works

### User Registration & Authentication
When a new user registers, SecureDrop prompts for a full name, email address, and password. The password is never stored in plain text — it is hashed using **SHA-256** before being written to `user.txt`. On subsequent launches, the entered password is hashed and compared against the stored hash to authenticate the user.

### Email Verification (MFA)
During registration, SecureDrop sends a **6-digit one-time verification code** to the provided email address via Gmail's SMTP server over SSL. The code expires after **15 minutes** and allows a maximum of **5 attempts**, after which registration is aborted. This step ensures that only the real owner of an email address can register it with the client.

### RSA Key Pair Generation
Upon successful registration, SecureDrop automatically generates a **2048-bit RSA key pair** (stored in `keys/private.pem` and `keys/public.pem`). These keys are generated using the `cryptography` library and are intended to support future encrypted communication between peers.

### Multithreading
SecureDrop runs two concurrent threads:

- **Listener Thread** — Runs in the background, continuously listening on **UDP port 5142** for broadcast messages from other clients on the network. It handles incoming contact discovery pings and file transfer requests, placing them on a thread-safe queue.
- **Main Thread** — Drives the interactive terminal loop, processing user commands and draining the incoming file transfer request queue before each prompt.

This design keeps the application responsive to incoming events while the user is actively using the CLI.

### Contact Discovery (UDP Broadcasting)
To check which contacts are online, SecureDrop broadcasts a `listing` message over UDP to the entire local network (`255.255.255.255`). Each peer that receives the broadcast checks whether it is the intended recipient, and if so, responds with a `listing-accept` message. The original sender then marks that contact as active in `contacts.json` along with their IP address. This process happens automatically when running the `list` or `send` commands.

### File Transfer (TLS over TCP)
File transfers are negotiated in two phases:

1. **Request Phase** — The sender broadcasts a `file-transfer-request` UDP message directly to the recipient's IP, including the sender's email and the file size. This message is placed onto the recipient's incoming request queue.
2. **Transfer Phase** — If the recipient accepts, they open a **TLS-secured TCP listener on port 5143**, loading an SSL certificate and key (`server.crt` / `server.key`). The sender then connects and streams the file in 4096-byte chunks. The received file is saved locally as `received_<timestamp>.bin`.

---

## Getting Started

### Prerequisites

- Python 3.8 or higher
- `pip` (Python package manager)
- An SSL certificate and key (see below)
- Devices must be on the **same local network** to discover each other

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/secure-drop.git
   cd secure-drop
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate      # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Generate a self-signed TLS certificate** (required for file transfers):
   ```bash
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout server.key -out server.crt
   ```
   Place `server.crt` and `server.key` in the project root directory.

### Running SecureDrop

```bash
python3 secure_drop.py
```

On first launch, you will be prompted to register a new user. After registration, exit and re-run the program to log in.

### Available Commands

Once logged in, the following commands are available at the `secure drop>` prompt:

| Command | Description |
|---------|-------------|
| `help`  | Display all available commands |
| `add`   | Add a new contact by name and email |
| `list`  | Discover and display which contacts are currently online |
| `send`  | Send a file to an online contact |
| `exit`  | Exit SecureDrop |

### Project File Structure

```
secure-drop/
├── secure_drop.py       # Main application source
├── requirements.txt     # Python dependencies
├── server.crt           # TLS certificate (you generate this)
├── server.key           # TLS private key (you generate this)
├── user.txt             # Stores registered user info (auto-created)
├── contacts.json        # Stores contact list (auto-created)
└── keys/
    ├── private.pem      # RSA private key (auto-generated on registration)
    └── public.pem       # RSA public key (auto-generated on registration)
```
