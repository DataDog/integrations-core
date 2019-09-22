COLOR_RED="\033[31;1m"
COLOR_RESET="\033[0m"

function retry {
  local n=1
  local max=3
  local delay=1
  while true; do
    "$@" && break || {
      if [[ $n -lt $max ]]; then
        ((n++))
        echo -e "\\n${COLOR_RED}The command \"${*}\" failed. Attempt $n/$max:${COLOR_RESET}\\n"
        sleep $delay;
      else
        echo -e "\\n${COLOR_RED}The command \"${*}\" failed after $n attempts.${COLOR_RESET}\\n"
        exit 1
      fi
    }
  done
}
