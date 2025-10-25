# How to Add Secrets to Agent Zero

Agent Zero uses a `.env` file to manage secrets and environment variables. This file is located in the root directory of the project. If it doesn't exist, you can create it.

## Adding a Hugging Face Hub API Key

To use models from the Hugging Face Hub, you need to add your API key to the `.env` file.

1.  **Open or create the `.env` file** in the root of your Agent Zero project.
2.  **Add the following line** to the file, replacing `<your-hugging-face-api-key>` with your actual API key:

    ```
    HUGGINGFACE_API_KEY=<your-hugging-face-api-key>
    ```

3.  **Save the file.**

Agent Zero will automatically load this key and use it to authenticate with the Hugging Face Hub.

## Other Secrets

You can add other secrets to the `.env` file in the same way. The application is designed to look for environment variables based on the provider name. For example, to add an API key for Anthropic, you would add the following line:

```
ANTHROPIC_API_KEY=<your-anthropic-api-key>
```

Refer to the `conf/model_providers.yaml` file for a list of supported providers and their corresponding environment variable names.