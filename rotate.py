#!/usr/bin/env python3

import argparse
import logging
import os
import sys


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

## définition du dossier contenant les backups et test des droits de ce dossier
if args.backupdir is None:
  backupdir = os.getcwd()
else:
  backupdir = args.backupdir

if not os.path.isdir(backupdir):
  logging.critical("'{}' n'est pas un dossier ou n'existe pas.".format(backupdir))
elif not os.access(backupdir, os.R_OK | os.W_OK | os.X_OK):
  logging.critical(
    "Le dossier de backup ({}) n'est pas accessible en lecture ou en écriture.".format(os.path.realpath(backupdir))
  )
  sys.exit(255)
else:
  backupdir = os.path.realpath(backupdir)
  logging.info("Le dossier de backup est '{}'.".format(backupdir))

# définition des durées de rétention si elle n'ont pas été définie
if not args.day and not args.week and not args.month and not args.year:
  logging.info(
    "Aucune durée de rétention n'est précisé, les valeurs par défaut sont appliquées : 7 jours, 5 semaines, 3 mois, 2 an."
  )
  args.day = 7
  args.week = 5
  args.month = 3
  args.year = 2

