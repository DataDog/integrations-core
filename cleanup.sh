while read dir; do
  # Check if the directory exists
  if [ -d "/Users/steven/dd/integrations-core/$dir" ]; then
    # Change to the directory and run the command
    echo "$dir"
    cd "/Users/steven/dd/integrations-core/$dir" && ruff check . --config ../pyproject.toml --fix && black --config ../pyproject.toml . && ruff check . --config ../pyproject.toml --add-noqa
  else
    echo "Directory $dir not found"
  fi
done < int.txt