# Connecting to Helmholtz (Blablador) and Other OpenAI-Compatible Endpoints

This document explains how to connect the application to an OpenAI-compatible endpoint, using the Helmholtz (Blablador) service as an example.

## Overview

The application is designed to work with any OpenAI-compatible API. This is achieved by using the **"Other OpenAI compatible"** provider option in the settings. When this provider is selected, you can specify a custom API base URL, which allows the application to communicate with your desired endpoint.

## Configuration Steps

To connect to an OpenAI-compatible endpoint, you need to configure the following settings in the web UI:

1.  **Select the Provider:**
    *   Navigate to the **Agent -> Chat Model** section in the settings.
    *   For the **"Chat model provider"** field, select **"Other OpenAI compatible"** from the dropdown menu.

2.  **Set the Model Name:**
    *   In the **"Chat model name"** field, enter the name of the model you want to use from the endpoint. For example, for the Blablador service, you might use a model name like `blablador-beta`.

3.  **Set the API Base URL:**
    *   In the **"Chat model API base URL"** field, enter the URL of the OpenAI-compatible endpoint. For the Blablador service, this would be your specific Helmholtz endpoint URL.

4.  **Provide the API Key:**
    *   Navigate to the **External -> API Keys** section.
    *   Find the **"Other OpenAI compatible"** field and enter your API key.

## How It Works

The application uses the `litellm` library to handle connections to various model providers. The `conf/model_providers.yaml` file defines the available providers. The "Other OpenAI compatible" provider is configured as follows:

```yaml
chat:
  # ... other providers
  other:
    name: Other OpenAI compatible
    litellm_provider: openai
```

This configuration tells `litellm` to use its `openai` integration for this provider. The `python/helpers/settings.py` file then loads this configuration and allows you to set the `chat_model_api_base`, which `litellm` uses as the `api_base` when making requests. This allows you to redirect the OpenAI requests to any compatible endpoint.
