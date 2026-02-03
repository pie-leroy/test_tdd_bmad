Feature: Synchronisation des user stories BMAD vers GitHub Project

Scenario: Déclenchement et synchro nominale
  Given un repository avec des user stories BMAD dans "_bmad-output/*" et un GitHub Project configuré
  When un push est effectué sur une branche
  Then une GitHub Action se déclenche et met à jour le statut des user stories dans le Project

Scenario: Aucune user story à synchroniser
  Given un repository sans user stories BMAD dans "_bmad-output/*"
  When un push est effectué sur une branche
  Then la GitHub Action se termine avec succès et indique qu'aucune user story n'a été synchronisée

Scenario: Erreur d'accès API GitHub
  Given un repository avec des user stories BMAD et un token GitHub invalide
  When un push est effectué sur une branche
  Then la GitHub Action échoue avec un message d'erreur explicite et aucun état n'est modifié dans le Project

Scenario: User story supprimée ou renommée
  Given un GitHub Project contenant une user story déjà synchronisée
  When un push est effectué et que la user story a été supprimée ou renommée dans "_bmad-output/*"
  Then la GitHub Action met à jour le Project pour refléter la suppression ou le nouveau nom
