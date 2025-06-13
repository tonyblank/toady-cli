# Publishing Guide for Toady CLI

This guide covers how to publish Toady CLI to PyPI using different methods.

## 🚀 Quick Start

### Option 1: Using Make Commands (Recommended)

```bash
# 1. Set up credentials (one-time)
make setup-publish

# 2. Test on TestPyPI first
make publish-test

# 3. Publish to production PyPI
make publish
```

### Option 2: Manual Commands

```bash
# Build and check
make build
twine check dist/*

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## 🔐 Credential Setup

### Method 1: API Tokens (Recommended)

1. **Create accounts:**
   - [TestPyPI](https://test.pypi.org/account/register/)
   - [PyPI](https://pypi.org/account/register/)

2. **Generate API tokens:**
   - [TestPyPI tokens](https://test.pypi.org/manage/account/token/)
   - [PyPI tokens](https://pypi.org/manage/account/token/)

3. **Configure `~/.pypirc`:**
   ```ini
   [distutils]
   index-servers = pypi testpypi

   [pypi]
   username = __token__
   password = pypi-YOUR_PRODUCTION_TOKEN_HERE

   [testpypi]
   repository = https://test.pypi.org/legacy/
   username = __token__
   password = pypi-YOUR_TEST_TOKEN_HERE
   ```

### Method 2: Environment Variables

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
```

## 🤖 Automated Publishing (CI/CD)

### GitHub Actions

The project includes automated publishing via GitHub Actions:

- **Automatic:** Publishes to PyPI when you create a GitHub release
- **Manual:** Use workflow dispatch to publish to TestPyPI

#### Setup for GitHub Actions:

1. **Add secrets to your repository:**
   - Go to: Settings → Secrets and variables → Actions
   - Add secrets:
     - `PYPI_API_TOKEN`: Your PyPI API token
     - `TEST_PYPI_API_TOKEN`: Your TestPyPI API token

2. **Create a release:**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   # Then create release on GitHub
   ```

3. **Manual testing:**
   - Go to Actions → Publish to PyPI → Run workflow
   - Select "testpypi" target

## 📋 Publishing Checklist

### Before Publishing:

- [ ] All tests pass: `make test`
- [ ] Version updated in `pyproject.toml`
- [ ] `CHANGELOG.md` updated
- [ ] Git tags created
- [ ] Package builds successfully: `make build`
- [ ] Package passes checks: `make check-publish`

### Publishing Process:

1. **Test on TestPyPI:**
   ```bash
   make publish-test
   ```

2. **Verify TestPyPI installation:**
   ```bash
   pip install --index-url https://test.pypi.org/simple/ toady-cli
   toady --version
   ```

3. **Publish to production:**
   ```bash
   make publish
   ```

4. **Verify production installation:**
   ```bash
   pip install toady-cli
   toady --version
   ```

## 🔄 Version Management

### Semantic Versioning

Follow [SemVer](https://semver.org/):
- `0.1.0` → `0.1.1` (patch: bug fixes)
- `0.1.0` → `0.2.0` (minor: new features)
- `0.1.0` → `1.0.0` (major: breaking changes)

### Update Version

1. **Update `pyproject.toml`:**
   ```toml
   version = "0.1.1"
   ```

2. **Update `src/toady/__init__.py`:**
   ```python
   __version__ = "0.1.1"
   ```

3. **Create git tag:**
   ```bash
   git add .
   git commit -m "Bump version to 0.1.1"
   git tag v0.1.1
   git push origin main --tags
   ```

## 📦 Package Maintenance

### Regular Updates

- Update dependencies: `make update`
- Run security audit: `uv pip audit`
- Update classifiers in `pyproject.toml`
- Keep README and documentation current

### Yanking Releases

If you need to remove a broken release:

```bash
# Via web interface (recommended)
# Go to PyPI project page → Manage → Yank release

# Via command line
twine upload --repository pypi --yank "Broken release" dist/old-version/*
```

## 🛠️ Troubleshooting

### Common Issues

1. **"File already exists"**
   - You can't re-upload the same version
   - Increment version number

2. **"Invalid authentication"**
   - Check API token format: `pypi-...`
   - Verify token has upload permissions

3. **"Package name taken"**
   - Choose a different name in `pyproject.toml`
   - Check availability on PyPI first

4. **"Metadata validation failed"**
   - Run `make check-publish` to see issues
   - Fix `pyproject.toml` metadata

### Getting Help

- [PyPI Help](https://pypi.org/help/)
- [Packaging User Guide](https://packaging.python.org/)
- [Twine Documentation](https://twine.readthedocs.io/)

## 🌟 Best Practices

1. **Always test on TestPyPI first**
2. **Use API tokens, not passwords**
3. **Keep credentials secure and rotated**
4. **Tag releases in git**
5. **Update changelog and documentation**
6. **Run full test suite before publishing**
7. **Use automated publishing for consistency**

## 📚 Additional Resources

- [Python Packaging Authority](https://www.pypa.io/)
- [Python Packaging User Guide](https://packaging.python.org/)
- [PEP 517 - Build System Interface](https://peps.python.org/pep-0517/)
- [PEP 518 - Build System Requirements](https://peps.python.org/pep-0518/)
