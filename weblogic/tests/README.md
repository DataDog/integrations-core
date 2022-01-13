# WebLogic Dev Readme

## DDev E2E
If you are spinning up a E2E for WebLogic for the first time, you will need to go to the Oracle Container Registry to accept the Oracle Standard Terms and Restrictions before you can successfully pull the image from the registry. 

1. Login to your account on https://container-registry.oracle.com
2. Search for "WebLogic" and click the `weblogic` repository. 
3. Follow the instructions to sign the License Agreement. The prompt is located on the right-hand side of the Oracle WebLogic Server repository page.
4. On your machine, run this command to authenticate against the Oracle Container Registry and enter your Oracle credentials:
   
    ```
    docker login container-registry.oracle.com
    ```
Now, you should be able to use `ddev` to start the weblogic E2E. 

Detailed Instructions for using the Oracle Container Registry are located [here](https://docs.oracle.com/en/operating-systems/oracle-linux/docker/docker-registry.html#docker-ocr-login). 