if (!(Test-Path -Path "./ca.crt") -or !(Test-Path -Path "./ca.key")) {
    Write-Host "Generating self-signed certificate..."
    & openssl req -x509 -newkey rsa:2048 -keyout ca.key -out ca.crt -days 365 -nodes -subj "/CN=localhost"
}

param(
    [string]$Cipher
)

Write-Host "Starting OpenSSL server on port 443 with cipher $Cipher..."
& openssl s_server `
    -accept 443 `
    -cert ca.crt `
    -key ca.key `
    -cipher $Cipher `
    -no_tls1_3 `
    -WWW
