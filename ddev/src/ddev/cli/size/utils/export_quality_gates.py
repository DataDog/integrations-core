from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.cli.application import Application
from ddev.cli.size.utils.size_model import Sizes, TotalsDict, convert_to_human_readable_size
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.size.utils.common_funcs import DeltaTypeGroup


def save_quality_gate_html(
    app: Application,
    modules: Sizes,
    compressed: bool,
    file_path: Path,
    baseline: str,
    threshold_percentage: float,
    baseline_size: TotalsDict,
    total_diff: TotalsDict,
    passes_quality_gate: bool,
) -> None:
    """
    Saves the modules list to HTML format, if the ouput is larger than the PR comment size max,
    it ouputs the short version.
    """
    html = str()
    html_headers = get_html_headers(threshold_percentage, baseline, passes_quality_gate)

    if not file_path.exists():
        file_path.write_text(html_headers, encoding="utf-8")

    type_str = (
        f"<h3>{'Compressed' if compressed else 'Uncompressed'} Size Changes "
        f"{'✅' if passes_quality_gate else '❌'}</h3>"
    )
    if not modules:
        html = f"{type_str}\n<h4>No size differences were found</h4>\n"

    else:
        groups = group_modules(modules)
        for (platform, py_version), delta_type_groups in groups.items():
            html_subheaders = str()

            sign_total = "+" if total_diff[platform][py_version] > 0 else ""
            threshold_bytes = baseline_size[platform][py_version] * threshold_percentage / 100
            threshold = convert_to_human_readable_size(threshold_bytes)

            html_subheaders += f"<details><summary><h4>&Delta; Size for {platform} and Python {py_version}:\n"
            html_subheaders += (
                f"{sign_total}{convert_to_human_readable_size(total_diff[platform][py_version])} "
                f"(Threshold: {threshold}) "
                f"{'✅' if total_diff[platform][py_version] < threshold_bytes else '❌'}</h4></summary>\n\n"
            )

            tables = str()

            tables += append_html_entry(delta_type_groups["New"], "Added")
            tables += append_html_entry(delta_type_groups["Removed"], "Removed")
            tables += append_html_entry(delta_type_groups["Modified"], "Modified")

            close_details = "</details>\n\n"

            html += f"{html_subheaders}\n{tables}\n{close_details}"

        html = f"<details><summary>{type_str}</summary>\n{html}\n</details>"

    with file_path.open(mode="a", encoding="utf-8") as f:
        f.write(html)

    app.display(f"HTML file saved to {file_path}")


def save_quality_gate_html_table(
    app: Application,
    modules: Sizes,
    compressed: bool,
    file_path: Path,
    baseline: str,
    threshold_percentage: float,
    baseline_size: TotalsDict,
    commit_size: TotalsDict,
    total_diff: TotalsDict,
    passes_quality_gate: bool,
) -> None:
    html_headers = get_html_headers(threshold_percentage, baseline, passes_quality_gate)

    if not file_path.exists():
        file_path.write_text(html_headers, encoding="utf-8")

    type_str = (
        f"<h3>{'Compressed' if compressed else 'Uncompressed'} Size Changes "
        f"{'✅' if passes_quality_gate else '❌'}</h3></summary>"
    )
    if not modules:
        final_html = f"{type_str}\n<h4>No size differences were found</h4>"
    else:
        table_rows = []
        groups = group_modules(modules)

        for (platform, py_version), delta_type_groups in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
            diff = total_diff[platform][py_version]
            sign_total = "+" if diff > 0 else ""
            delta_compressed_size = f"{sign_total}{convert_to_human_readable_size(diff)}"

            threshold_bytes = baseline_size[platform][py_version] * threshold_percentage / 100
            threshold_sign = "+" if threshold_bytes > 0 else ""
            threshold = f"{threshold_sign}{convert_to_human_readable_size(threshold_bytes)}"

            sign_added = "+" if delta_type_groups["New"]["Total"] > 0 else ""
            sign_removed = "+" if delta_type_groups["Removed"]["Total"] > 0 else ""
            sign_modified = "+" if delta_type_groups["Modified"]["Total"] > 0 else ""

            total_added = f"{sign_added}{convert_to_human_readable_size(delta_type_groups['New']['Total'])}"
            total_removed = f"{sign_removed}{convert_to_human_readable_size(delta_type_groups['Removed']['Total'])}"
            total_modified = f"{sign_modified}{convert_to_human_readable_size(delta_type_groups['Modified']['Total'])}"

            current_size = f"{convert_to_human_readable_size(commit_size[platform][py_version])}"
            delta_pct = (
                total_diff[platform][py_version] / baseline_size[platform][py_version] * 100
                if baseline_size[platform][py_version] != 0
                else 0
            )
            delta_percentage = f"{sign_total}{round(delta_pct, 2)}%"

            status = "❌" if diff >= threshold_bytes else "✅"

            table_rows.append(
                "<tr>"
                f"<td>{platform}</td>"
                f"<td>{py_version}</td>"
                f"<td>{current_size}</td>"
                f"<td>{total_added}</td>"
                f"<td>{total_removed}</td>"
                f"<td>{total_modified}</td>"
                f"<td>{delta_compressed_size}</td>"
                f"<td>{delta_percentage}</td>"
                f"<td>{threshold}</td>"
                f"<td>{status}</td>"
                "</tr>"
            )

        html_table = (
            "<table>\n"
            "  <thead>\n"
            "    <tr>\n"
            "      <th>Platform</th>\n"
            "      <th>Python</th>\n"
            "      <th>Current Size</th>\n"
            "      <th>&Delta; Added</th>\n"
            "      <th>&Delta; Removed</th>\n"
            "      <th>&Delta; Modified</th>\n"
            "      <th>&Delta; Total</th>\n"
            "      <th>&Delta; Total %</th>\n"
            "      <th>Threshold</th>\n"
            "      <th>Status</th>\n"
            "    </tr>\n"
            "  </thead>\n"
            "  <tbody>\n"
            f"{''.join(table_rows)}\n"
            "  </tbody>\n"
            "</table>"
        )

        final_html = f"<details><summary>{type_str}</summary>\n{html_table}\n</details>"

    with file_path.open(mode="a", encoding="utf-8") as f:
        f.write(final_html)

    app.display(f"HTML file saved to {file_path}")


def get_html_headers(threshold_percentage: float, baseline: str, passes_quality_gate: bool) -> str:
    html_headers = (
        "<h2>⛔ Size Quality Gates Not Passed</h2>"
        if not passes_quality_gate
        else "<h2>✅ Size Quality Gates Passed</h2>"
    )
    html_headers += (
        "<p>"
        "These Quality Gates apply only to dependencies and integrations packaged with the Datadog Agent.\n\n"
        f"<strong>Threshold:</strong> {threshold_percentage}% per platform and Python version<br>"
        "<strong>Compared to commit:</strong> "
        f'<a href="https://github.com/DataDog/integrations-core/commit/{baseline}">{baseline[:7]}</a>'
        "</p>"
    )

    return html_headers


def group_modules(
    modules: Sizes,
) -> dict[tuple[str, str], dict[str, DeltaTypeGroup]]:
    groups: dict[tuple[str, str], dict[str, DeltaTypeGroup]] = {}

    for m in modules.root:
        platform_key = (m.platform, m.python_version)
        delta_type = m.delta_type

        if platform_key not in groups:
            groups[platform_key] = {
                "New": {"Modules": Sizes([]), "Total": 0},
                "Removed": {"Modules": Sizes([]), "Total": 0},
                "Modified": {"Modules": Sizes([]), "Total": 0},
            }

        if delta_type in groups[platform_key]:
            groups[platform_key][delta_type]["Modules"].append(m)
            groups[platform_key][delta_type]["Total"] += m.size_bytes

    return groups


def append_html_entry(delta_type_group: DeltaTypeGroup, type: str) -> str:
    html = str()
    if delta_type_group["Total"] != 0:
        sign = "+" if delta_type_group["Total"] > 0 else ""
        html += (
            f"<b>{type}:</b> {len(delta_type_group['Modules'])} item(s), {sign}"
            f"{convert_to_human_readable_size(delta_type_group['Total'])}\n"
        )
        html += "<table><tr><th>Type</th><th>Name</th><th>Version</th><th>Size Delta</th>"

        html += "<th>Percentage</th></tr>\n" if type not in ["Added", "Removed"] else "</tr>\n"

        for e in delta_type_group["Modules"].root:
            html += f"<tr><td>{e.type}</td><td>{e.name}</td><td>{e.version}</td>"
            html += f"<td>{e.size}</td>"
            html += f"<td>{e.percentage}%</td></tr>\n" if type not in ["Added", "Removed"] else "</tr>\n"
        html += "</table>\n"
    else:
        html += f"No {type.lower()} dependencies/integrations\n\n"

    return html
