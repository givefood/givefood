timeout = 1200
# Six vCPUs are shared with five other Django sites on this box, and this app
# had more workers than any of them - 8, against opencompanies' 4 for 13x the
# database traffic (460 txn/s vs 36). Halved rather than cut to what traffic
# alone implies, because the 1200s timeout above says some endpoints tie a
# worker up for a long time and the spare capacity absorbs that.
workers = 4