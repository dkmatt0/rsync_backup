#!/usr/bin/env python3

import argparse
import datetime as dt
import logging
import os
import re
import shutil
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

## définition des variables permettant le tri des dates de backup
regex = re.compile(r"^(?P<year>[0-9]{4})(?P<month>(0[0-9]|1[0-2]))(?P<day>([0-2][0-9]|3[01]))$")
dates = {"ignored": set(), "year": {}, "month": {}, "week": {}, "day": {}}
most_recent_date = ""
dt_most_recent_date = {"year": 1970, "month": (1970, 1), "week": (1970, 1), "day": (1970, 1, 1)}
all_dates = {}

## tri les dates de backup
for date in os.listdir(backupdir):
  dirname = os.path.join(backupdir, date)
  if os.path.isdir(dirname) and regex.match(date):
    reg_date = regex.match(date)
    ## on vérifie que c'est une date valide
    try:
      dt_date = dt.date(int(reg_date.group("year")), int(reg_date.group("month")), int(reg_date.group("day")))
      date_iso = dt_date.isocalendar()
    except:
      logging.warning("'{}' sera ignoré car ce n'est pas une date valide.".format(dirname))
      # dates["ignored"].add(date)
      continue

    ## définie les varibles utiles au condition pour filtrer la première date de chaque période
    date_format = {
      "year": dt_date.year,
      "month": (dt_date.year, dt_date.month),
      "week": (date_iso[0], date_iso[1]),
      "day": (dt_date.year, dt_date.month, dt_date.day),
    }

    ## on ajoute la date à la liste des dates valides
    all_dates[date] = []

    ## on fait le test pour avoir la première date de chaque période ainsi que la dernière date globale
    for period in ("year", "month", "week", "day"):
      if most_recent_date < date:
        most_recent_date = date
        dt_most_recent_date = date_format
      if date_format[period] not in dates[period] or dates[period][date_format[period]] > date:
        dates[period][date_format[period]] = date

  else:
    logging.warning("'{}' n'est pas un dossier ou le dossier n'est pas dans un format de date reconnu.".format(dirname))
    # dates["ignored"].add(date)

## vérifie si au moins un dossier de backup est inventorié
if len(all_dates) == 0:
  logging.critical("Aucun backup n'a pu être inventorié dans '{}'.".format(backupdir))
  sys.exit()

## sélection des sauvegardes à garder par périodes
for period in ("year", "month", "week", "day"):
  keep_number = getattr(args, period)
  if keep_number != 0:
    period_dates = sorted(dates[period].values())
    dt_list_dates = sorted(dates[period])
    if dt_list_dates[-1] == dt_most_recent_date[period]:
      all_dates[period_dates[-1]].append(period + "_in_progress")
      period_dates.remove(dates[period][dt_list_dates[-1]])
    if keep_number > 0:
      for keep_date in period_dates[keep_number * -1 :]:
        all_dates[keep_date].append(period)
    else:
      for keep_date in period_dates:
        all_dates[keep_date].append(period)

## affichage et action pour chaque dossier de backup
for date in sorted(all_dates):
  dirname = os.path.join(backupdir, date)
  if len(all_dates[date]) > 0:
    logging.info("'{}' est marqué à conserver : {}.".format(dirname, ", ".join(all_dates[date])))
  else:
    logging.info("'{}' est marqué à supprimer.".format(dirname))
    if not args.dry_run:
      try:
        shutil.rmtree(dirname)
        logging.debug("{} vient d'être supprimé.".format(dirname))
      except:
        logging.error("Une erreur a eu lieu lors de la suppression de {}".format(dirname))
