# WebLogic Dev Readme

## ddev E2E
If you are spinning up a E2E environment for WebLogic for the first time, you will need to go to the Oracle Container Registry and accept the Oracle Standard Terms and Restrictions before you can successfully pull the image from the registry.

1. Log into your Oracle account on https://container-registry.oracle.com (or create an account if you do not have one).
2. Search for "WebLogic" and click the `weblogic` repository. 
3. Follow the instructions to sign the License Agreement. The prompt is located on the right side of the Oracle WebLogic Server repository page.
4. On your machine, run the following command to authenticate against the Oracle Container Registry and then enter your Oracle credentials:
   
    ```
    docker login container-registry.oracle.com
    ```
Use `ddev` to start the WebLogic E2E environment. 

See [detailed instructions](https://docs.oracle.com/en/operating-systems/oracle-linux/docker/docker-registry.html#docker-ocr-login) for using the Oracle Container Registry. 

## Accessing the Admin Console UI

1. Navigate to http://localhost:7001/console in your browser.
2. See [login credentials](./compose/weblogic/properties/docker-build/domain_security.properties).