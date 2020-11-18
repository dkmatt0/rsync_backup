#!/usr/bin/env python3

import argparse
import logging
import os


## définition des arguments du programmme
parser = argparse.ArgumentParser()
parser.add_argument("-b", "--backupdir", help="home directory to store backup (current directory by default)")
parser.add_argument("-q", "--quiet", action="store_true", help="be more quiet")
parser.add_argument("-v", "--verbose", action="count", help="increase output verbosity", default=0)
parser.add_argument("-n", "--dry-run", action="store_true", help="dry run")
args = parser.parse_args()

## définition des niveaux de log
loglevel_list = (logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)

## gestion de la verbosité
if args.quiet:
  loglevel_min = 1
else:
  loglevel_min = LOG_LEVEL

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

## Affichage d'un message lorsque le mode dry-run est actif et définition de l'argument pour rsync
if args.dry_run:
  logging.info(
    "Mode dry run actif, aucune modification ne sera fait (sauf la création des dossiers de destination des sauvegardes si ils n'existe pas)."
  )
  rsync_dry_run = "--dry-run"
else:
  rsync_dry_run = ""

## définition du dossier contenant les backups et test des droits de ce dossier
if args.backupdir is None:
  backupdir = os.getcwd()
else:
  backupdir = args.backupdir

if not os.path.isdir(backupdir):
  logging.critical("'{}' n'est pas un dossier ou n'existe pas.".format(backupdir))
  sys.exit(255)
elif not os.access(backupdir, os.R_OK | os.W_OK | os.X_OK):
  logging.critical(
    "Le dossier de backup ({}) n'est pas accessible en lecture ou en écriture.".format(os.path.realpath(backupdir))
  )
  sys.exit(255)
else:
  backupdir = os.path.realpath(backupdir)
  logging.info("Le dossier de backup est '{}'.".format(backupdir))

