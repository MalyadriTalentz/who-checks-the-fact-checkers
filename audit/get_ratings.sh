#!/bin/sh
# Stream the 2026-11-14 noteRatings release and keep only ratings of the 800 sampled notes -> cache/sample_ratings.tsv (not committed).
B=https://ton.twimg.com/birdwatch-public-data/2026/11/14/noteRatings
out=cache/sample_ratings.tsv; : > $out; i=0
while :; do
  f=$(printf "ratings-%05d.zip" $i)
  code=$(curl -s -m 60 -r 0-0 -o /dev/null -w "%{http_code}" $B/$f)
  [ "$code" = "206" ] || { [ "$code" = "404" ] && break; sleep 5; continue; }
  curl -s --retry 5 $B/$f | funzip | awk -F'\t' -v first=$i 'NR==FNR{if(FNR>1){split($0,a,","); ids[a[1]]=1} next} FNR==1{if(first==0)print; next} ($1 in ids)' audit/sample.csv - >> $out
  echo "part $i done: $(wc -l < $out) lines"; i=$((i+1))
done
