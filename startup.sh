#!/bin/bash

LOG_FILE="$HOME/qr_log.txt"

# --- crontabへの自動登録処理 ---
# 追加したいcronジョブを定義
# start_qr.shまでのフルパスを取得してcronジョブを定義する

while true; do
	read -p "cronに登録するスクリプトのフルパスを入力してください(例:start_qr.sh)(find, ls, pwd, exitも利用可):" SCRIPT_PATH

	case "$SCRIPT_PATH" in
		"ls")
			ls -F
			;;
		"pwd")
			pwd
			;;
		find\ *)
			eval "$SCRIPT_PATH"
			;;
		whereis\ *)
			eval "$SCRIPT_PATH"
			;;
		"exit" | "quit")
			echo "スクリプトを中断します。"
			exit 0
			;;
		*)
			a
			# 入力されたパスが存在し、かつ実行可能ファイルであるかチェック
			if [ -n "$SCRIPT_PATH" ] && [ -f "$SCRIPT_PATH" ] && [ -x "$SCRIPT_PATH" ]; then
				break # 正しければループを抜ける
			else
				# から入力の場合は何も表示せず、それ以外はエラーを表示
				if [ -n "$SCRIPT_PATH" ]; then
				
					echo "エラー: ファイルが存在しないか、実行権限がありません。"
					echo "正しいフルパスを入力してください(start_qr.sh)"
				fi
			fi
			;;
	esac
done


echo "登録するスクリプト: $SCRIPT_PATH"

#SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
#SCRIPT_PATH="${SCRIPT_DIR}/$(basename "$0")"
#CRON_JOB="@reboot ${SCRIPT_PATH}"
CRON_JOB="@reboot ${SCRIPT_PATH}"

# すでに同じジョブが登録されているか確認
(crontab -l 2>/dev/null | grep -qF "$CRON_JOB")

# grepの終了コードが0でない場合(見つからなかった場合)のみジョブを追加
if [ $? -ne 0 ]; then
	# 既存のcrontab設定に新しいジョブを追記
	(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
	echo "crontabにrebootジョブを登録しました。" >> $LOG_FILE
else
	echo "crontabのrebootジョブはすでに登録済みです。" >>$LOG_FILE
fi
