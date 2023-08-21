package main

import (
	"fmt"
	"log"
	"net"
)

func main() {
	ifaces, err := net.Interfaces()
	if err != nil {
		log.Fatal(err)
	}

	fmt.Println("devices:")
	for _, i := range ifaces {
		fmt.Println("  - name:", i.Name)
		addrs, _ := i.Addrs()
		for _, addr := range addrs {
			fmt.Println("    - address: ", addr)
		}
	}

}
