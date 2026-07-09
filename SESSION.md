# roll_plugin_monitor Session

## Purpose

Raspberry Pi 환경에서 MQTT 메시지를 구독해 롤 좌/우 값과 롤 온도를 표시하는 별도 UI 앱이다.

## Decisions

- 기존 `roll_monitor_plugin_legacy`는 수정하지 않고 참고만 한다.
- 새 앱은 `0_services/roll_plugin_monitor`에 독립 구성한다.
- Modbus 직접 읽기는 제거하고 MQTT subscribe 기반으로 동작한다.
- Tkinter UI는 메인 스레드에서만 갱신하고, MQTT 콜백은 큐에 읽기 결과만 넣는다.
- `iot_gathering` tags payload와 기존 legacy payload를 둘 다 지원한다.

## 2026-06-25

- 새 프로젝트 골격 생성.
- MQTT payload 정규화 테스트 추가.
- 설정, 상태 병합, MQTT 클라이언트, Tkinter UI, 실행 엔트리 추가.
- Raspberry Pi Docker 배포 방향으로 `Dockerfile`, `docker-compose.example.yml` 추가.
- compose 기준 런타임 파일은 `./roll_plugin_monitor/config.ini`, `./roll_plugin_monitor/logs/`에 둔다.
- 앱 로그 파일 기본 경로는 `/app/logs/roll_plugin_monitor.log`로 설정한다.
- Docker build context에서 로컬 런타임 폴더와 Python cache가 제외되도록 `.dockerignore`를 추가한다.
- 앱/도커 이미지 버전을 `1.0.1`으로 맞춘다.
- Docker image tag 기준은 `btx/roll_plugin_monitor:1.0.1`로 둔다.
- Raspberry Pi 배포용 registry image는 `203.228.107.184:5000/btx/roll_plugin_monitor:1.0.1`이고 `linux/arm64`로 빌드/푸시한다.
