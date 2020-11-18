#!/usr/bin/env python3

import argparse
import datetime as dt
import logging
import os
import shutil
import subprocess
import sys
import time
import copy


## variables par défaut
MAX_SIMULTANEOUS_BACKUP = 2
REMOTE_DIR = "/home"
SSH_REMOTE_USER = "root"
SSH_ARGS = "-o StrictHostKeyChecking=no -o batchmode=yes -o passwordauthentication=no"
RSYNC_ARGS = "-av --del"
LOG_LEVEL = 4  # 1: CRITICAL, 2: ERROR, 3: WARNING, 4: INFO, 5: DEBUG


## définition des arguments du programmme
parser = argparse.ArgumentParser()
parser.add_argument("-b", "--backupdir", help="home directory to store backup (current directory by default)")
parser.add_argument("-r", "--remotedir", help="remote directory to save (/home by default)", default=REMOTE_DIR)
parser.add_argument("-s", "--server-file", help="file listing all servers to save")
parser.add_argument("-m", "--max", help="max simultaneous backup", default=MAX_SIMULTANEOUS_BACKUP)
parser.add_argument("-u", "--ssh-user", help="ssh user for rsync", default=SSH_REMOTE_USER)
parser.add_argument("-A", "--ssh-args", help="ssh arguments for rsync", default=SSH_ARGS)
parser.add_argument("-a", "--rsync-args", help="rsync arguments", default=RSYNC_ARGS)
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

## test et chargement de la liste des serveurs (à sauvegarder)
if args.server_file is None:
  logging.critical("Aucune liste de serveur n'a été fourni")
  sys.exit(255)
elif not os.path.isfile(args.server_file):
  logging.critical("'{}' n'est pas un fichier ou n'existe pas.".format(args.server_file))
  sys.exit(255)
elif not os.access(args.server_file, os.R_OK):
  logging.critical(
    "La liste des machines ({}) n'est pas accessible en lecture.".format(os.path.realpath(args.server_file))
  )
  sys.exit(255)
else:
  server_file = os.path.realpath(args.server_file)
  logging.info("Le fichier listant les serveurs est '{}'.".format(server_file))
list_server_file = open(server_file, "r")
list_servers = list_server_file.readlines()
list_servers = set([x.strip() for x in list_servers if x.strip() != ""])
logging.debug(list_servers)

## variable et boucle permettant le lancement des sauvegardes sur les serveurs choisi.
iter_servers = iter(list_servers)
runnning_servers = {}
finish_servers = {}

stop_next = False
servers = []
logging.info("Lancement des sauvegardes.")
while servers or stop_next == False:
  ## selectionne les prochaines serveurs sur lesquels lancé la sauvegarde
  i = 0
  while len(servers) < args.max and stop_next == False:
    next_value = next(iter_servers, None)
    if next_value is not None:
      servers.append(next_value)
    else:
      stop_next = True

  ## boucle pour lancer les sauvegardes pour X serveurs en simultannée
  i = 0
  while i < len(servers):
    server = servers[i]

    ## lance le test de disponibilité de la machine (ping)
    if server not in runnning_servers:
      logging.debug(f"Tentative de ping pour {server}.")
      runnning_servers[server] = dict(
        ping_process=subprocess.Popen(
          f"ping -c 2 {server}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True
        )
      )

    ## vérifie le statut du ping et récupère les logs
    elif "ping" not in runnning_servers[server]:
      if runnning_servers[server]["ping_process"].poll() is not None:
        runnning_servers[server]["ping_output"] = "".join(runnning_servers[server]["ping_process"].stdout.readlines())
        if runnning_servers[server]["ping_process"].poll() == 0:
          runnning_servers[server]["ping"] = True
          logging.debug(f"La machine {server} répond correctement au ping.")
        else:
          runnning_servers[server]["ping"] = False
          logging.debug(f"La machine {server} ne répond pas correctement au ping.")
          finish_servers[server] = copy.copy(runnning_servers[server])
          del runnning_servers[server]
          del servers[i]
          continue

    ## lance la création des dossiers et le backup si ping est ok
    elif runnning_servers[server]["ping"]:
      backupdir_server = os.path.join(backupdir, server)
      if not os.path.isdir(os.path.join(backupdir, server)):
        logging.debug(f"Création du dossier {backupdir_server}")
        if not args.dry_run:
          logging.info(f"Malgré le mode dry run, le dossier {backupdir_server} sera réellement créé.")
        os.mkdir(backupdir_server)
      if "rsync_process" not in runnning_servers[server]:
        logging.debug(f"Lancement du rsync pour {server}")
        runnning_servers[server]["rsync_process"] = subprocess.Popen(
          f"rsync -e 'ssh -l {args.ssh_user} {args.ssh_args}' {args.rsync_args} {rsync_dry_run} {server}:{args.remotedir}/ {backupdir_server}/current",
          shell=True,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          universal_newlines=True,
        )
      ## vérifie le statut du backup et récupère les logs
      elif "rsync" not in runnning_servers[server]:
        if runnning_servers[server]["rsync_process"].poll() is not None:
          runnning_servers[server]["rsync_output"] = "".join(
            runnning_servers[server]["rsync_process"].stdout.readlines()
          )
          if runnning_servers[server]["rsync_process"].poll() == 0:
            runnning_servers[server]["rsync"] = True
            logging.debug(f"Rsync terminé pour {server}")
          else:
            runnning_servers[server]["rsync"] = False
            logging.debug(f"Erreur rsync pour {server}")
            finish_servers[server] = copy.copy(runnning_servers[server])
            del runnning_servers[server]
            del servers[i]
            continue

      ## si sauvegarde ok dans current, copie (en mode hardlink) vers un dossier avec la date du jour
      elif runnning_servers[server]["rsync"]:
        src_dir = os.path.join(backupdir, server, "current")
        dst_dir = os.path.join(backupdir, server, dt.date.today().strftime("%Y%m%d"))
        if os.path.exists(dst_dir):
          logging.debug(f"Le dossier de destination existe ({dst_dir}), suppression de l'ancien dossier.")
          if not args.dry_run:
            shutil.rmtree(dst_dir)
        logging.debug(f"Copie de {src_dir} vers {dst_dir}.")
        if not args.dry_run:
          shutil.copytree(
            os.path.join(backupdir_server, "current"), os.path.join(backupdir_server, dst_dir), copy_function=os.link
          )
        finish_servers[server] = copy.copy(runnning_servers[server])
        del runnning_servers[server]
        del servers[i]
        continue

    i += 1
    time.sleep(0.5)  # pause pour ne pas saturer le cpu


## affiche un compte-rendu de la sauvegarde
for server in sorted(finish_servers):
  if finish_servers[server]["ping"] is False:
    logging.error(f"{server}: NOK ping")
    logging.debug(finish_servers[server]["ping_output"])
  elif finish_servers[server]["rsync"] is False:
    logging.error(f"{server}: NOK rsync")
    logging.debug(finish_servers[server]["rsync_output"])
  else:
    logging.info(f"{server}: OK")
