n=1
max=3
delay=1
while true; do
  "$@" && break || {
    if [[ $n -lt $max ]]; then
      ((n++))
      echo ""
      echo "[RETRY] The command \"${*}\" failed. Attempt $n/$max:"
      echo ""
      sleep $delay;
    else
      echo ""
      echo "[RETRY] The command \"${*}\" failed after $n attempts."
      echo ""
      exit 1
    fi
  }
done
