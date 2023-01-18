// @@@SNIPSTART hello-world-project-template-go-activity
package app

import (
	"context"
	"fmt"
)

func ComposeGreeting(ctx context.Context, name string) (string, error) {
	greeting := fmt.Sprintf("Hello %s!", name)
	return greeting, nil
}

// @@@SNIPEND
