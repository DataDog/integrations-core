FROM mcr.microsoft.com/windows/nanoserver:ltsc2022

# Copy files to Windows container paths
COPY start-server.ps1 C:\usr\local\bin\start-server.ps1
COPY ca.* C:\tmp\

# Install OpenSSL and bash equivalents for Windows
# Add Chocolately package manager for flexibility
RUN choco install -y openssl light

# Expose port 443
EXPOSE 443
