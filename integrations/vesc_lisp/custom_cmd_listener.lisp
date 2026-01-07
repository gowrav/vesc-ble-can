;; =========================================================
;; VESC Custom Command Listener (Reference Integration)
;;
;; Receives COMM_CUSTOM_APP_DATA payloads (single byte)
;; and performs simple directional motor commands.
;;
;; Command mapping:
;;   0x00 -> Stop
;;   0x01 -> Forward
;;   0x02 -> Reverse
;;
;; Intended to be used with:
;;   - vesc-ble-can (Python BLE ↔ CAN library)
;;   - VESC Tool QML UI
;;
;; NOTE:
;; - Temporarily switches app mode for direct RPM control
;; - Restores previous app after command execution
;; =========================================================

;; ==========================
;; Config
;; ==========================
(def SPEED_ERPM 4000)
(def RUN_LENGTH 0.2)

;; ==========================
;; Handle CMD
;; ==========================
(defun handle-cmd (data)
  {
    (if (eq data 1) {
        (print "Forward")
        (conf-set 'app-to-use 3)
        (set-rpm SPEED_ERPM)
        (sleep RUN_LENGTH)
        (conf-set 'app-to-use 2)
        })

    (if (eq data 2) {
        (print "Reverse")
        (conf-set 'app-to-use 3)
        (set-rpm (- 0 SPEED_ERPM))
        (sleep RUN_LENGTH)
        (conf-set 'app-to-use 2)
        })

    (if (eq data 0) {
        (print "Stop")
        (conf-set 'app-to-use 3)
        (set-rpm 0)
        (sleep RUN_LENGTH)
        (conf-set 'app-to-use 2)
        })
  }
)

;; ==========================
;; RX Handler
;; ==========================
(defun proc-data (data) {
  (if (> (buflen data) 0)
      (handle-cmd (bufget-u8 data 0)))
})

(defun event-handler () {
  (loopwhile t
    (recv
      ((event-data-rx . (? data)) (proc-data data))
      (_ nil))
  )
})

(event-register-handler (spawn event-handler))
(event-enable 'event-data-rx)

(print "Custom CMD listener active")
