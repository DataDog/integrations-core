# Check if the server certificate and key exist
if (!(Test-Path "C:\ProgramData\ssl\certs\server.crt") -or !(Test-Path "C:\ProgramData\ssl\private\server.key")) {
    Write-Host "Generating self-signed certificate..."
    
    # Create directories for certificates if they don't exist
    New-Item -ItemType Directory -Force -Path "C:\ProgramData\ssl\certs"
    New-Item -ItemType Directory -Force -Path "C:\ProgramData\ssl\private"

    # Generate self-signed certificate
    & openssl req -x509 -newkey rsa:2048 `
        -keyout "C:\ProgramData\ssl\private\server.key" `
        -out "C:\ProgramData\ssl\certs\server.crt" `
        -days 365 -nodes `
        -subj "/CN=localhost"
}

# Get the cipher from the command-line argument
$Cipher = $args[0]
if (-not $Cipher) {
    Write-Host "No cipher provided. Exiting..."
    exit 1
}

# Start the OpenSSL server on port 443
Write-Host "Starting OpenSSL server on port 443 with cipher $Cipher..."
& openssl s_server `
    -accept 443 `
    -cert "C:\ProgramData\ssl\certs\server.crt" `
    -key "C:\ProgramData\ssl\private\server.key" `
    -cipher $Cipher `
    -no_tls1_3 `
    -WWW
