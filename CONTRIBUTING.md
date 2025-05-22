# Contributing to ArtCafe.ai Agent Framework

Thank you for your interest in contributing to the ArtCafe.ai Agent Framework! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## How to Contribute

There are several ways you can contribute to the ArtCafe.ai Agent Framework:

1. **Reporting Bugs**: If you find a bug, please open an issue with a clear description and steps to reproduce.
2. **Suggesting Enhancements**: If you have ideas to enhance the framework, please open an issue to discuss it.
3. **Pull Requests**: Submit PRs to fix bugs or add features.
4. **Documentation**: Help improve documentation, examples, and tutorials.
5. **Testing**: Add or improve tests for the framework.

## Development Setup

Follow these steps to set up your development environment:

1. Fork the repository
2. Clone your fork:
   ```
   git clone https://github.com/your-username/agent-framework.git
   cd agent-framework
   ```
3. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install development dependencies:
   ```
   pip install -e ".[dev]"
   ```

## Pull Request Process

1. Create a new branch from `main` for your changes:
   ```
   git checkout -b feature/your-feature-name
   ```
   
2. Make your changes, following our coding conventions.

3. Add or update tests as necessary.

4. Run the tests to ensure they pass:
   ```
   pytest
   ```

5. Update the documentation to reflect your changes, if applicable.

6. Commit your changes following our commit message guidelines.

7. Push to your fork and submit a pull request.

## Commit Message Guidelines

We follow a simplified version of the [Conventional Commits](https://www.conventionalcommits.org/) standard:

- Format: `<type>: <description>`
- Example: `feat: Add support for Cohere LLM provider`

Common types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring without functionality changes
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependency updates, etc.

## Code Style

We use the following tools to ensure code quality:

- **Black**: For code formatting
- **isort**: For import sorting
- **Flake8**: For linting
- **mypy**: For type checking

You can run these tools with:
```
black .
isort .
flake8
mypy .
```

## Licensing

By contributing to the ArtCafe.ai Agent Framework, you agree that your contributions will be licensed under the project's [MIT license](LICENSE).

## Release Process

Our release process follows these steps:

1. We create a release branch from `main`.
2. Testing is performed on the release branch.
3. Version numbers are updated according to [Semantic Versioning](https://semver.org/).
4. A new release is created on GitHub with release notes.
5. The package is published to PyPI.

## Questions?

If you have any questions or need help, please:

1. Check the [Documentation](https://docs.artcafe.ai/agent-framework)
2. Open an issue on GitHub
3. Contact us at support@artcafe.ai

Thank you for contributing to the ArtCafe.ai Agent Framework!