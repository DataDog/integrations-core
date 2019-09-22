COLOR_RED="\033[31;1m"
COLOR_RESET="\033[0m"

n=1
max=3
delay=1
while true; do
  "$@" && break || {
    if [[ $n -lt $max ]]; then
      ((n++))
      echo ""
      echo "${COLOR_RED}The command \"${*}\" failed. Attempt $n/$max:${COLOR_RESET}"
      echo ""
      sleep $delay;
    else
      echo ""
      echo "${COLOR_RED}The command \"${*}\" failed after $n attempts.${COLOR_RESET}"
      echo ""
      exit 1
    fi
  }
done
