# Contributing

## Setting up Dev Environment

This project uses VSCode devcontainers. In VSCode you can do Ctrl+Shift+P and `Clone Repository in Container Volume`.

Then in the terminal run:

```bash
cd ./src/jupyrest/
sh dev_setup.sh
code .
```

## Running Tests

All tests are available in the VSCode Test Explorer. Prior to running the tests, start the [Azurite Storage Emulator](https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azurite?tabs=visual-studio-code) and the Grpc Server. You can do this in the Run and Debug Tab, select `Start Grpc Server`.