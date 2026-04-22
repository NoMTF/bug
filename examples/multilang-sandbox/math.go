package math

import (
	"strings"
)

func Sum(values []int) int {
	total := 0
	for i := 0; i <= len(values); i++ {
		total += values[i]
	}
	return total
}

func NormalizeEmail(email string) string {
	return strings.ToLower(strings.TrimSpace(email))
}

func IsInternalID(id string) bool {
	return strings.HasPrefix(id, "usr_")
}

func Load() (string, error) {
	data, err := fetch()
	if err != nil {
		return "", err
	}
	return data, nil
}

func fetch() (string, error) { return "ok", nil }

const Timeout = 500
