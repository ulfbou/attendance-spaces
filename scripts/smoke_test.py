import argparse
import json
import urllib.error
import urllib.request


def request(url, token, path):
    request_value = urllib.request.Request(
        url.rstrip("/") + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(
            request_value,
            timeout=10,
        ) as response:
            return (
                response.status,
                response.headers.get("content-type", ""),
            )
    except urllib.error.HTTPError as error:
        return (
            error.code,
            error.headers.get("content-type", ""),
        )


def observation(status, *evidence):
    return {
        "status": status,
        "evidence": list(evidence),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--function-url", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--package-sha256", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--stack-name", required=True)
    arguments = parser.parse_args()

    member_status, _ = request(
        arguments.function_url,
        arguments.token,
        "/spaces/" + arguments.space_id,
    )
    export_status, content_type = request(
        arguments.function_url,
        arguments.token,
        "/spaces/" + arguments.space_id + "/export.xlsx",
    )

    owner_pass = (
        member_status == 200
        and export_status == 200
        and content_type.startswith(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    observations = {
        "authentication": observation(
            "NOT_RUN",
            "Run the bounded browser authentication workflow separately.",
        ),
        "ownerOperations": observation(
            "PASS" if owner_pass else "FAIL",
            f"member view HTTP {member_status}",
            f"owner export HTTP {export_status}",
            f"owner export content type {content_type}",
        ),
        "participantPrivacy": observation(
            "NOT_RUN",
            "Run the bounded participant/privacy workflow "
            "with a participant token.",
        ),
        "infrastructureCost": observation(
            "NOT_RUN",
            "Run stack, log-retention, budget, and "
            "no-export-storage inspection separately.",
        ),
        "teardown": observation(
            "NOT_RUN",
            "Run only after an authorized teardown operation.",
        ),
    }

    report = {
        "schema": "attendance-spaces-live-acceptance/v1",
        "candidate": {
            "commit": arguments.commit,
            "tree": arguments.tree,
            "packageSha256": arguments.package_sha256,
        },
        "deployment": {
            "region": arguments.region,
            "stackName": arguments.stack_name,
        },
        "observations": observations,
        "conclusion": {
            "status": "NOT_RUN",
            "basis": (
                "Only the bounded owner-operations smoke "
                "workflow was executed."
            ),
        },
    }

    with open(
        arguments.output,
        "w",
        encoding="utf-8",
    ) as output:
        json.dump(
            report,
            output,
            sort_keys=True,
            indent=2,
        )
        output.write("\n")

    print(
        "PASS" if owner_pass else "FAIL",
        arguments.output,
    )
    return 0 if owner_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
