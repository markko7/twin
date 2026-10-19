import os
import shutil
import subprocess

APP_FILES = ["server.py", "lambda_handler.py", "context.py", "resources.py"]

# Everything happens inside the container; only the final zip crosses the bind mount.
# Writing thousands of small files to a Windows-mounted disk (e.g. /mnt/c from WSL) is very slow.
BUILD_SCRIPT = f"""set -e
pip install --target /tmp/pkg -r /var/task/requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --upgrade --root-user-action=ignore
cd /var/task
cp {" ".join(f for f in APP_FILES if os.path.exists(f))} /tmp/pkg/
if [ -d data ]; then cp -r data /tmp/pkg/data; fi
cd /tmp/pkg
python -m zipfile -c /var/task/lambda-deployment.zip .
"""


def main():
    """Build lambda-deployment.zip using the AWS Lambda Python 3.12 image."""
    print("Creating Lambda deployment package...")
    for path in ["lambda-package", "deps.tar"]:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    if os.path.exists("lambda-deployment.zip"):
        os.remove("lambda-deployment.zip")

    print("Installing dependencies and zipping inside Lambda runtime container...")
    subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{os.getcwd()}:/var/task",
            "--platform", "linux/amd64",
            "--entrypoint", "",
            "public.ecr.aws/lambda/python:3.12",
            "/bin/sh", "-c", BUILD_SCRIPT,
        ],
        check=True,
    )

    size_mb = os.path.getsize("lambda-deployment.zip") / (1024 * 1024)
    print(f"Created lambda-deployment.zip ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
