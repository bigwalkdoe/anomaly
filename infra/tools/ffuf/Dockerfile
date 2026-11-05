FROM golang:1.22-alpine AS build
RUN go install github.com/ffuf/ffuf/v2@latest

FROM alpine:3.20
COPY --from=build /go/bin/ffuf /usr/local/bin/ffuf
ENTRYPOINT ["ffuf"]
