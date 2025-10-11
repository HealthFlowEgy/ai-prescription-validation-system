# Contributing to HealthFlow AI Prescription Validation System

We are excited to have you contribute to the HealthFlow project! To ensure a smooth and efficient development process, we have adopted a simplified branching strategy. This document outlines the branching model and the process for contributing to the project.

## Branching Strategy

We use a simple two-branch strategy:

- **`main`**: This branch represents the production-ready code. All code on this branch is fully tested and deployed to the production environment. Direct pushes to `main` are not allowed. All changes must come through a pull request from the `develop` branch.

- **`develop`**: This is the primary development branch. All new features, bug fixes, and other changes are developed in this branch. When the `develop` branch is stable and ready for a release, it is merged into the `main` branch.

### Workflow

1.  **Create a feature branch (optional but recommended for large features):**
    - For larger features, you can create a feature branch from `develop`. This allows you to work on the feature in isolation without affecting the `develop` branch.
    - Feature branches should be named descriptively, e.g., `feature/new-ocr-engine`.

2.  **Commit your changes:**
    - Make your changes and commit them to your feature branch or directly to the `develop` branch for smaller changes.
    - Write clear and concise commit messages.

3.  **Push your changes:**
    - Push your changes to the remote repository.

4.  **Create a Pull Request (PR):**
    - If you used a feature branch, create a PR from your feature branch to `develop`.
    - If you committed directly to `develop`, you will create a PR from `develop` to `main` when it's time for a release.

5.  **Code Review:**
    - All PRs must be reviewed and approved by at least one other team member.
    - The reviewer will check for code quality, correctness, and adherence to the project's coding standards.

6.  **Merge the PR:**
    - Once the PR is approved, it can be merged.
    - For feature branches, merge into `develop`.
    - For releases, merge from `develop` into `main`.

## CI/CD Pipeline

We have a comprehensive CI/CD pipeline that automates the testing and deployment process.

- **Continuous Integration (CI):** The CI pipeline runs on every push to `develop` and on all pull requests to `main` and `develop`. It performs the following checks:
    - Code quality and linting
    - Backend and frontend tests
    - Security scans
    - Database migration tests
    - Docker image builds

- **Continuous Deployment (CD):** The CD pipeline runs on every push to `develop` and `main`:
    - Pushes to `develop` are deployed to the **staging** environment.
    - Pushes to `main` are deployed to the **production** environment.

## Getting Started

1.  Clone the repository:
    ```bash
    git clone https://github.com/HealthFlowEgy/ai-prescription-validation-system.git
    ```

2.  Install the dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Start contributing!

If you have any questions, please feel free to reach out to the HealthFlow Team.

