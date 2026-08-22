# Binder Environment Setup

This directory contains configuration files for running TrenTorch in cloud environments via [Binder](https://mybinder.org) and [Google Colab](https://colab.research.google.com).

> **Currently non-functional**: TrenTorch is a private repo, and neither Binder nor Colab can clone a private GitHub repo. These launch buttons will start working the moment the repo goes public; no other setup is needed at that point.

## Files

- **`requirements.txt`**: Python dependencies for the Binder environment
- **`postBuild`**: Script that runs after environment setup to install TrenTorch

## How It Works

### Binder

When users click the "Launch Binder" button on any notebook page in the TrenTorch documentation:

1. Binder reads `binder/requirements.txt` to install Python dependencies
2. Binder runs `binder/postBuild` which:
   - Installs the TrenTorch package (`pip install -e .`)
   - Generates student notebooks from `src/*.py` files using Jupytext
   - Populates `modules/` with ready-to-use Jupyter notebooks
3. Users get a fully configured JupyterLab environment with TrenTorch and all notebooks ready to use

**Note**: The `modules/` directory is gitignored because notebooks are generated from the source `.py` files. This ensures students always get notebooks that match the current code.

**Binder URL Format:**
```
https://mybinder.org/v2/gh/Shashank-Tripathi-07/TrenTorch/main
```

### Google Colab

Colab launch buttons automatically:
1. Clone the repository
2. Install dependencies from `binder/requirements.txt`
3. Run setup commands (users may need to manually run `pip install -e .`)

**Colab URL Format:**
```
https://colab.research.google.com/github/Shashank-Tripathi-07/TrenTorch/blob/main/modules/path/to/notebook.ipynb
```

## Testing

To test your Binder setup:

1. **Test Binder Build:**
   ```bash
   # Visit: https://mybinder.org/v2/gh/Shashank-Tripathi-07/TrenTorch/main
   # Or use the badge:
   [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/Shashank-Tripathi-07/TrenTorch/main)
   ```

2. **Verify Installation:**
   Once Binder launches, test in a notebook:
   ```python
   import trentorch
   print(trentorch.__version__)
   ```

3. **Check Available Resources:**
   ```python
   import os
   print("Modules:", os.listdir("modules"))
   print("Milestones:", os.listdir("milestones"))
   ```

## Troubleshooting

### Binder Build Fails

- Check `binder/requirements.txt` for syntax errors
- Verify `binder/postBuild` has execute permissions (`chmod +x binder/postBuild`)
- Review Binder build logs at: https://mybinder.org/v2/gh/Shashank-Tripathi-07/TrenTorch/main?urlpath=lab/tree/logs%2Fbuild.log

### Colab Import Errors

- Ensure `binder/requirements.txt` includes all dependencies
- Users may need to run: `!pip install -e .` in a Colab cell
- Check that the repository is public (Colab can't access private repos)

### Package Not Found

- Verify `postBuild` script runs `pip install -e .` correctly
- Check that `pyproject.toml` is in the repository root
- Ensure all dependencies in `requirements.txt` are compatible

## Deployment Environments

Three deployment environments are supported:

1. **JupyterHub** (institutional server)
   - 8-core/32GB supports ~50 students
   - Best for classroom use

2. **Google Colab** (zero installation)
   - Best for MOOCs and self-paced learning
   - No setup required from students

3. **Local Installation** (`pip install trentorch`)
   - Best for self-paced learning and development
   - Full control over environment

## Keeping Dependencies Updated

When updating dependencies:

1. Update `requirements.txt` (root) - for local development
2. Update `binder/requirements.txt` - for Binder/Colab
3. Keep versions synchronized where possible

## References

- [Binder Documentation](https://mybinder.readthedocs.io/)
- [Jupyter Book Launch Buttons](https://jupyterbook.org/en/stable/interactive/launchbuttons.html)
- [Google Colab GitHub Integration](https://colab.research.google.com/github/)
