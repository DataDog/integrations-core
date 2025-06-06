#!/usr/bin/env python3
import os
import subprocess

def generate_proto():
    proto_file = os.path.join(os.path.dirname(__file__), 'test_message.proto')
    output_dir = os.path.dirname(__file__)
    
    # Generate Python code from proto file
    subprocess.run([
        'protoc',
        f'--python_out={output_dir}',
        proto_file
    ], check=True)

if __name__ == '__main__':
    generate_proto() 