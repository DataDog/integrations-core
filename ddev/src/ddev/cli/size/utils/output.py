from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Optional

from ddev.cli.application import Application
from ddev.cli.size.utils.general import convert_to_human_readable_size
from ddev.cli.size.utils.models import (
    CommitEntryPlatformWithDelta,
    CommitEntryWithDelta,
    DeltaTypeGroup,
    FileDataEntry,
    SizeMode,
)
from ddev.utils.fs import Path

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.patches import Patch

import squarify


def save_json(
    app: Application,
    file_path: str,
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
) -> None:
    if modules == []:
        return

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(modules, f, default=str, indent=2)
    app.display(f"JSON file saved to {file_path}")


def save_csv(
    app: Application,
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
    file_path: str,
) -> None:
    if modules == []:
        return

    headers = [k for k in modules[0].keys() if k not in ["Size", "Delta"]]

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")

        for row in modules:
            f.write(",".join(format(str(row.get(h, ""))) for h in headers) + "\n")

    app.display(f"CSV file saved to {file_path}")


def format(s: str) -> str:
    """
    Wraps the string in double quotes if it contains a comma, for safe CSV formatting.
    """
    return f'"{s}"' if "," in s else s


def save_markdown(
    app: Application,
    title: str,
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
    file_path: str,
) -> None:
    if modules == []:
        return

    headers = [k for k in modules[0].keys() if "Bytes" not in k]

    # Group modules by platform and version
    grouped_modules = {(modules[0].get("Platform", ""), modules[0].get("Python_Version", "")): [modules[0]]}
    for module in modules[1:]:
        platform = module.get("Platform", "")
        version = module.get("Python_Version", "")
        key = (platform, version)
        if key not in grouped_modules:
            grouped_modules[key] = []
        if any(str(value).strip() not in ("", "0", "0001-01-01") for value in module.values()):
            grouped_modules[key].append(module)

    lines = []
    lines.append(f"# {title}")
    lines.append("")

    for (platform, version), group in grouped_modules.items():
        if platform and version:
            lines.append(f"## Platform: {platform}, Python Version: {version}")
        elif platform:
            lines.append(f"## Platform: {platform}")
        elif version:
            lines.append(f"## Python Version: {version}")
        else:
            lines.append("## Other")

        lines.append("")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in group:
            lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")
        lines.append("")

    markdown = "\n".join(lines)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(markdown)
    app.display(f"Markdown table saved to {file_path}")


def print_table(
    app: Application,
    mode: str,
    modules: list[FileDataEntry] | list[CommitEntryWithDelta] | list[CommitEntryPlatformWithDelta],
) -> None:
    if modules == []:
        return

    columns = [col for col in modules[0].keys() if "Bytes" not in col]
    modules_table: dict[str, dict[int, str]] = {col: {} for col in columns}
    for i, row in enumerate(modules):
        if row.get("Size_Bytes") == 0:
            continue
        for key in columns:
            modules_table[key][i] = str(row.get(key, ""))

    app.display_table(mode, modules_table)


def save_quality_gate_html(
    app: Application,
    modules: list[FileDataEntry],
    compressed: bool,
    file_path: Path,
    old_commit: str,
    threshold_percentage: float,
    old_size: dict[tuple[str, str], int],
    total_diff: dict[tuple[str, str], int],
    passes_quality_gate: bool,
) -> None:
    """
    Saves the modules list to HTML format, if the ouput is larger than the PR comment size max,
    it ouputs the short version.
    """
    html = str()
    html_headers = get_html_headers(threshold_percentage, old_commit, passes_quality_gate)

    if not file_path.exists():
        file_path.write_text(html_headers, encoding="utf-8")

    type_str = (
        f"<h3>{'Compressed' if compressed else 'Uncompressed'} Size Changes "
        f"{'✅' if passes_quality_gate else '❌'}</h3>"
    )
    if modules == []:
        html = f"{type_str}\n<h4>No size differences were found</h4>\n"

    else:
        groups = group_modules(modules)
        for (platform, py_version), delta_type_groups in groups.items():
            html_subheaders = str()

            sign_total = "+" if total_diff[(platform, py_version)] > 0 else ""
            threshold_bytes = old_size[(platform, py_version)] * threshold_percentage / 100
            threshold = convert_to_human_readable_size(threshold_bytes)

            html_subheaders += f"<details><summary><h4>&Delta; Size for {platform} and Python {py_version}:\n"
            html_subheaders += (
                f"{sign_total}{convert_to_human_readable_size(total_diff[(platform, py_version)])} "
                f"(Threshold: {threshold}) "
                f"{'✅' if total_diff[(platform, py_version)] < threshold_bytes else '❌'}</h4></summary>\n\n"
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
    modules: list[FileDataEntry],
    compressed: bool,
    file_path: Path,
    old_commit: str,
    threshold_percentage: float,
    old_size: dict[tuple[str, str], int],
    new_size: dict[tuple[str, str], int],
    total_diff: dict[tuple[str, str], int],
    passes_quality_gate: bool,
) -> None:
    html_headers = get_html_headers(threshold_percentage, old_commit, passes_quality_gate)

    if not file_path.exists():
        file_path.write_text(html_headers, encoding="utf-8")

    type_str = (
        f"<h3>{'Compressed' if compressed else 'Uncompressed'} Size Changes "
        f"{'✅' if passes_quality_gate else '❌'}</h3></summary>"
    )
    if modules == []:
        final_html = f"{type_str}\n<h4>No size differences were found</h4>"
    else:
        table_rows = []
        groups = group_modules(modules)

        for (platform, py_version), delta_type_groups in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
            diff = total_diff.get((platform, py_version), 0)
            sign_total = "+" if diff > 0 else ""
            delta_compressed_size = f"{sign_total}{convert_to_human_readable_size(diff)}"

            threshold_bytes = old_size.get((platform, py_version), 0) * threshold_percentage / 100
            threshold_sign = "+" if threshold_bytes > 0 else ""
            threshold = f"{threshold_sign}{convert_to_human_readable_size(threshold_bytes)}"

            sign_added = "+" if delta_type_groups["New"]["Total"] > 0 else ""
            sign_removed = "+" if delta_type_groups["Removed"]["Total"] > 0 else ""
            sign_modified = "+" if delta_type_groups["Modified"]["Total"] > 0 else ""

            total_added = f"{sign_added}{convert_to_human_readable_size(delta_type_groups['New']['Total'])}"
            total_removed = f"{sign_removed}{convert_to_human_readable_size(delta_type_groups['Removed']['Total'])}"
            total_modified = f"{sign_modified}{convert_to_human_readable_size(delta_type_groups['Modified']['Total'])}"

            current_size = f"{convert_to_human_readable_size(new_size[(platform, py_version)])}"
            delta_percentage = (
                f"{sign_total}{round(total_diff[(platform, py_version)] / old_size[(platform, py_version)] * 100, 2)}%"
            )

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


def get_html_headers(threshold_percentage: float, old_commit: str, passes_quality_gate: bool) -> str:
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
        f'<a href="https://github.com/DataDog/integrations-core/commit/{old_commit}">{old_commit[:7]}</a>'
        "</p>"
    )

    return html_headers


def group_modules(
    modules: list[FileDataEntry],
) -> dict[tuple[str, str], dict[str, DeltaTypeGroup]]:
    groups: dict[tuple[str, str], dict[str, DeltaTypeGroup]] = {}

    for m in modules:
        platform_key = (m.get("Platform", ""), m.get("Python_Version", ""))
        delta_type = m.get("Delta_Type", "")

        if platform_key not in groups:
            groups[platform_key] = {
                "New": {"Modules": [], "Total": 0},
                "Removed": {"Modules": [], "Total": 0},
                "Modified": {"Modules": [], "Total": 0},
            }

        if delta_type in groups[platform_key]:
            groups[platform_key][delta_type]["Modules"].append(m)
            groups[platform_key][delta_type]["Total"] += m.get("Size_Bytes", 0)

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

        for e in delta_type_group["Modules"]:
            html += f"<tr><td>{e.get('Type', '')}</td><td>{e.get('Name', '')}</td><td>{e.get('Version', '')}</td>"
            html += f"<td>{e.get('Size', '')}</td>"
            html += f"<td>{e.get('Percentage', '')}%</td></tr>\n" if type not in ["Added", "Removed"] else "</tr>\n"
        html += "</table>\n"
    else:
        html += f"No {type.lower()} dependencies/integrations\n\n"

    return html


def export_format(
    app: Application,
    format: list[str],
    modules: list[FileDataEntry],
    mode: SizeMode,
    platform: str | None,
    py_version: str | None,
    compressed: bool,
) -> None:
    size_type = "compressed" if compressed else "uncompressed"
    name = f"{mode.value}_{size_type}"
    if platform:
        name += f"_{platform}"
    if py_version:
        name += f"_{py_version}"
    for output_format in format:
        if output_format == "csv":
            csv_filename = f"{name}.csv"
            save_csv(app, modules, csv_filename)

        elif output_format == "json":
            json_filename = f"{name}.json"
            save_json(app, json_filename, modules)

        elif output_format == "markdown":
            markdown_filename = f"{name}.md"
            save_markdown(app, mode.value, modules, markdown_filename)


def plot_treemap(
    app: Application,
    modules: list[FileDataEntry],
    title: str,
    show: bool,
    mode: SizeMode,
    path: Optional[str] = None,
) -> None:
    import matplotlib.pyplot as plt

    if modules == []:
        return

    # Initialize figure and axis
    plt.figure(figsize=(12, 8))
    ax = plt.gca()
    ax.set_axis_off()

    # Calculate the rectangles
    if mode is SizeMode.STATUS:
        rects, colors, legend_handles = plot_status_treemap(modules)

    if mode is SizeMode.DIFF:
        rects, colors, legend_handles = plot_diff_treemap(modules)

    draw_treemap_rects_with_labels(ax, rects, modules, colors)

    # Finalize layout and show/save plot
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)

    plt.title(title, fontsize=16)

    plt.legend(handles=legend_handles, title="Type", loc="center left", bbox_to_anchor=(1.0, 0.5))
    plt.subplots_adjust(right=0.8)
    plt.tight_layout()

    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        plt.savefig(path, bbox_inches="tight", format="png")
        app.display(f"Treemap saved to {path}")
    if show:
        plt.show()


def plot_status_treemap(
    modules: list[FileDataEntry] | list[FileDataEntry],
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Calculate the area of the rectangles
    sizes = [mod["Size_Bytes"] for mod in modules]
    norm_sizes = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(norm_sizes, 0, 0, 100, 100)

    # Define the colors for each type
    cmap_int = plt.get_cmap("Purples")
    cmap_dep = plt.get_cmap("Reds")

    # Assign colors based on type and normalized size
    colors = []
    max_area = max(norm_sizes) or 1
    for mod, area in zip(modules, norm_sizes, strict=False):
        intensity = scale_colors_treemap(area, max_area)
        if mod["Type"] == "Integration":
            colors.append(cmap_int(intensity))
        elif mod["Type"] == "Dependency":
            colors.append(cmap_dep(intensity))
        else:
            colors.append("#999999")
    # Define the legend
    legend_handles = [
        Patch(color=plt.get_cmap("Purples")(0.6), label="Integration"),
        Patch(color=plt.get_cmap("Reds")(0.6), label="Dependency"),
    ]
    return rects, colors, legend_handles


def plot_diff_treemap(
    modules: list[FileDataEntry] | list[FileDataEntry],
) -> tuple[list[dict[str, float]], list[tuple[float, float, float, float]], list[Patch]]:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    # Define the colors for each type
    cmap_pos = plt.get_cmap("Oranges")
    cmap_neg = plt.get_cmap("Blues")

    # Separate in negative and positive differences
    positives = [mod for mod in modules if mod["Size_Bytes"] > 0]
    negatives = [mod for mod in modules if mod["Size_Bytes"] < 0]

    sizes_pos = [mod["Size_Bytes"] for mod in positives]
    sizes_neg = [abs(mod["Size_Bytes"]) for mod in negatives]

    sum_pos = sum(sizes_pos)
    sum_neg = sum(sizes_neg)

    canvas_area = 50 * 100

    # Determine dominant side and scale layout accordingly
    if sum_pos >= sum_neg:
        norm_sizes_pos = [s / sum_pos * canvas_area for s in sizes_pos]
        norm_sizes_neg = [s / sum_pos * canvas_area for s in sizes_neg]
        rects_neg = squarify.squarify(norm_sizes_neg, 0, 0, 50, 100)
        rects_pos = squarify.squarify(norm_sizes_pos, 50, 0, 50, 100)

    else:
        norm_sizes_neg = [s / sum_neg * canvas_area for s in sizes_neg]
        norm_sizes_pos = [s / sum_neg * canvas_area for s in sizes_pos]
        rects_neg = squarify.squarify(norm_sizes_neg, 0, 0, 50, 100)
        rects_pos = squarify.squarify(norm_sizes_pos, 50, 0, 50, 100)

    # Merge layout and module lists
    rects = rects_neg + rects_pos
    modules = negatives + positives

    # Assign colors based on type and normalized size
    colors = []
    max_area = max(norm_sizes_pos + norm_sizes_neg) or 1

    for area in norm_sizes_neg:
        intensity = scale_colors_treemap(area, max_area)
        colors.append(cmap_neg(intensity))

    for area in norm_sizes_pos:
        intensity = scale_colors_treemap(area, max_area)
        colors.append(cmap_pos(intensity))

    legend_handles = [
        Patch(color=plt.get_cmap("Oranges")(0.7), label="Increase"),
        Patch(color=plt.get_cmap("Blues")(0.7), label="Decrease"),
    ]

    return rects, colors, legend_handles


def scale_colors_treemap(area: float, max_area: float) -> float:
    vmin = 0.3
    vmax = 0.65
    return vmin + (area / max_area) * (vmax - vmin)


def draw_treemap_rects_with_labels(
    ax: Axes,
    rects: list[dict],
    modules: list[FileDataEntry] | list[FileDataEntry],
    colors: list[tuple[float, float, float, float]],
) -> None:
    from matplotlib.patches import Rectangle

    """
    Draw treemap rectangles with their assigned colors and optional text labels.

    Args:
        ax: Matplotlib Axes to draw on.
        rects: List of rectangle dicts from squarify, each with 'x', 'y', 'dx', 'dy'.
        modules: List of modules associated with each rectangle (same order).
        colors: List of colors for each module (same order).
    """
    for rect, mod, color in zip(rects, modules, colors, strict=False):
        x, y, dx, dy = rect["x"], rect["y"], rect["dx"], rect["dy"]

        # Draw the rectangle with a white border
        ax.add_patch(Rectangle((x, y), dx, dy, color=color, ec="white"))

        # Determine font size based on rectangle area
        MIN_FONT_SIZE = 6
        MAX_FONT_SIZE = 12
        FONT_SIZE_SCALE = 0.4
        AVG_SIDE = (dx * dy) ** 0.5  # Geometric mean
        font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, AVG_SIDE * FONT_SIZE_SCALE))

        # Determine the info for the labels
        name = mod["Name"]
        size_str = f"({mod['Size']})"

        # Estimate if there's enough space for text
        CHAR_WIDTH_FACTOR = 0.1  # Width of each character relative to font size
        CHAR_HEIGHT_FACTOR = 0.5  # Minimum height for readable text

        name_fits = (len(name) + 2) * font_size * CHAR_WIDTH_FACTOR < dx and dy > font_size * CHAR_HEIGHT_FACTOR
        size_fits = (len(size_str) + 2) * font_size * CHAR_WIDTH_FACTOR < dx
        both_fit = dy > font_size * CHAR_HEIGHT_FACTOR * 2  # Enough room for two lines

        # If the rectangle is too small, skip the label
        if dx < 5 or dy < 5:
            label = None

        # If the name doesn't fit, truncate it with "..."
        elif not name_fits and dx > 5:
            max_chars = int(dx / (font_size * CHAR_WIDTH_FACTOR)) - 2
            if max_chars >= 4:
                name = name[: max_chars - 3] + "..."
                name_fits = True

        # Build the label based on available space
        if name_fits and size_fits and both_fit:
            label = f"{name}\n{size_str}"  # Two-line label
        elif name_fits:
            label = name
        else:
            label = None

        # Draw label centered inside the rectangle
        if label:
            ax.text(
                x + dx / 2,
                y + dy / 2,
                label,
                va="center",
                ha="center",
                fontsize=font_size,
                color="black",
            )
