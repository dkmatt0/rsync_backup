#!/usr/bin/env python3

import argparse
import logging


## définition des arguments du programmme
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--day", type=int, help="keep N daily backups", default=0)
parser.add_argument("-w", "--week", type=int, help="keep N weekly backups", default=0)
parser.add_argument("-m", "--month", type=int, help="keep N monthly backups", default=0)
parser.add_argument("-y", "--year", type=int, help="keep N yearly backups", default=0)
parser.add_argument("-q", "--quiet", action="store_true", help="be more quiet")
parser.add_argument("-v", "--verbose", action="count", help="increase output verbosity", default=0)
parser.add_argument("-b", "--backupdir", help="home backup directory (current directory by default)")
parser.add_argument("-n", "--dry-run", action="store_true", help="dry run")
args = parser.parse_args()

## définition des niveaux de log
loglevel_list = (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)

## gestion de la verbosité
if args.quiet:
  loglevel_min = 1
else:
  loglevel_min = 3

if args.verbose + loglevel_min >= 5:
  loglevel = loglevel_list[4]
elif args.verbose + loglevel_min >= 1:
  loglevel = loglevel_list[args.verbose + loglevel_min - 1]
else:
  loglevel = loglevel_list[loglevel_min]

## activation des logs
logging.basicConfig(
  filename=None, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=loglevel
)

