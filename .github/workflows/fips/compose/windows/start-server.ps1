if (!(Test-Path -Path "C:/app/ca.crt") -or !(Test-Path -Path "C:/app/ca.key")) {
    Write-Host "Generating self-signed certificate..."
    & openssl req -x509 -newkey rsa:2048 -keyout C:/app/ca.key -out C:/app/ca.crt -days 365 -nodes -subj "/CN=localhost"
}

param(
    [string]$Cipher
)

Write-Host "Starting OpenSSL server on port 443 with cipher $Cipher..."
& openssl s_server `
    -accept 443 `
    -cert C:/app/ca.crt `
    -key C:/app/ca.key `
    -cipher $Cipher `
    -no_tls1_3 `
    -WWW
