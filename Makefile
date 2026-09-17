# Kisayollar. Her hedefin altindaki komut dogrudan da calistirilabilir; make
# onlari yalnizca tek yerde topluyor. Windows'ta make kurulu olmayabilir --
# o durumda asagidaki komutlari oldugu gibi elle calistirin.
PYTHON ?= python

.DEFAULT_GOAL := help
.PHONY: help lint test run clean

help:
	@echo "make lint   - ruff (kural seti ve gerekceleri ruff.toml icinde)"
	@echo "make test   - import kontrolu + pytest (ham veri gerektirmez)"
	@echo "make run    - tum pipeline, 12 adim (ham veri gerekir)"
	@echo "make clean  - yalnizca uretilen rapor/figur/ara veriyi sil"
	@echo ""
	@echo "tek adim    - $(PYTHON) run_all.py --only clean   (adim listesi: --list)"

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) tools/check_imports.py
	$(PYTHON) -m pytest

run:
	$(PYTHON) run_all.py

# Silme kurali run_all.py icinde: yalnizca uretilen ciktilar gider, elle
# yazilan docs/ kalir. Buraya cikplak bir `rm -rf reports/*` yazilmasi, o
# kuralin iki yerde tekrarlanmasi demek olurdu.
clean:
	$(PYTHON) run_all.py --clean
