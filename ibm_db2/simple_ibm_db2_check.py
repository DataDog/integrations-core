#!/usr/bin/env python3
"""
Simple IBM DB2 Connection Check
This is a minimal version that only handles:
1. Import prerequisites
2. Load configuration
3. Attempt connection
"""

import os
import sys
from datadog_checks.base.utils.platform import Platform

# Handle Windows DLL path for ibm_db
if Platform.is_windows():
    # After installing ibm_db, dll path of dependent library of clidriver must be set before importing the module
    # Ref: https://github.com/ibmdb/python-ibmdb/#installation
    embedded_lib = os.path.dirname(os.path.abspath(os.__file__))
    os.add_dll_directory(os.path.join(embedded_lib, 'site-packages', 'clidriver', 'bin'))

try:
    import ibm_db
    print("✓ Successfully imported ibm_db")
except ImportError as e:
    print(f"✗ Failed to import ibm_db: {e}")
    sys.exit(1)


class SimpleIbmDb2Check:
    """Simplified IBM DB2 connection checker"""
    
    def __init__(self, config=None):
        """Initialize with configuration"""
        # Default configuration
        self.config = config or {}
        
        # Load connection parameters
        self._db = self.config.get('db', '')
        self._username = self.config.get('username', '')
        self._password = self.config.get('password', '')
        self._host = self.config.get('host', '')
        self._port = self.config.get('port', 50000)
        self._security = self.config.get('security', 'none')
        self._tls_cert = self.config.get('tls_cert')
        self._connection_timeout = self.config.get('connection_timeout')
        
        print("✓ Configuration loaded successfully")
        print(f"  Database: {self._db}")
        print(f"  Host: {self._host or 'local'}")
        print(f"  Port: {self._port}")
        print(f"  Username: {self._username}")
        print(f"  Security: {self._security}")
    
    def get_connection_string(self):
        """Build connection string based on configuration"""
        if self._host:
            # Remote connection
            target = f'database={self._db};hostname={self._host};port={self._port};protocol=tcpip;uid={self._username};pwd={self._password}'
            
            if self._security == 'ssl':
                target = f'{target};security=ssl;'
            
            if self._tls_cert:
                target = f'{target};security=ssl;sslservercertificate={self._tls_cert}'
            
            if self._connection_timeout:
                target = f'{target};connecttimeout={self._connection_timeout}'
                
            return target, '', ''  # username/password are in connection string for remote
        else:
            # Local connection
            return self._db, self._username, self._password
    
    def scrub_connection_string(self, conn_str):
        """Remove sensitive information from connection string for logging"""
        if 'pwd=' in conn_str:
            return conn_str.split('pwd=')[0] + 'pwd=***'
        return conn_str
    
    def test_connection(self):
        """Test connection to IBM DB2"""
        print("\n--- Testing Connection ---")
        
        try:
            target, username, password = self.get_connection_string()
            
            print(f"Attempting to connect with: {self.scrub_connection_string(target)}")
            
            # Connection options - get column names in lower case
            connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}
            
            # Attempt connection
            connection = ibm_db.connect(target, username, password, connection_options)
            
            if connection:
                print("✓ Connection successful!")
                
                # Test a simple query
                try:
                    cursor = ibm_db.exec_immediate(connection, "SELECT CURRENT_TIMESTAMP FROM SYSIBM.SYSDUMMY1")
                    row = ibm_db.fetch_assoc(cursor)
                    if row:
                        print(f"✓ Query test successful. Current time: {row}")
                    else:
                        print("✓ Connection works but query returned no results")
                except Exception as query_error:
                    print(f"⚠ Connection works but query failed: {query_error}")
                
                # Close connection
                ibm_db.close(connection)
                print("✓ Connection closed successfully")
                return True
            else:
                print("✗ Connection failed - no connection object returned")
                return False
                
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False


def main():
    """Main function to run the simple check"""
    print("=== Simple IBM DB2 Connection Check ===\n")
    
    # Example configuration - modify these values for your environment
    config = {
        'db': 'SAMPLE',  # Your database name
        'username': 'db2admin',  # Your username
        'password': 'your_password',  # Your password
        'host': 'localhost',  # Your host (leave empty for local connection)
        'port': 50000,  # Your port
        'security': 'none',  # 'none' or 'ssl'
        # 'tls_cert': '/path/to/cert.crt',  # Uncomment if using SSL
        # 'connection_timeout': 30,  # Uncomment to set timeout
    }
    
    # You can also load config from environment variables
    if os.getenv('DB2_HOST'):
        config.update({
            'host': os.getenv('DB2_HOST'),
            'db': os.getenv('DB2_DATABASE', config['db']),
            'username': os.getenv('DB2_USERNAME', config['username']),
            'password': os.getenv('DB2_PASSWORD', config['password']),
            'port': int(os.getenv('DB2_PORT', config['port'])),
        })
        print("✓ Using configuration from environment variables")
    
    # Create checker and test connection
    checker = SimpleIbmDb2Check(config)
    success = checker.test_connection()
    
    if success:
        print("\n🎉 All checks passed!")
        return 0
    else:
        print("\n❌ Connection check failed!")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 