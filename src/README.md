# AI Work Item Assistant Backend

Backend service for generating Azure DevOps work items using Azure OpenAI and optionally creating them in Azure DevOps.

## Features

- Azure OpenAI with Entra ID
- Azure Key Vault integration
- Soft gate for vague/random input
- Generate work item draft
- Optional create in Azure DevOps

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
