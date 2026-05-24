import subprocess
import time


while True:

    print(
        "\nChecking for new files...\n"
    )

    subprocess.run([
        "python",
        "pipeline.py"
    ])

    print(
        "\nWaiting for next cycle...\n"
    )

    time.sleep(300)