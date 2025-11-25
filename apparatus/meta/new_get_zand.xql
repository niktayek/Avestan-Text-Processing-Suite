xquery version "3.1";

import module namespace functx="http://www.functx.com" at "app_functions.xqm";
import module namespace http = "http://expath.org/ns/http-client";

declare namespace fn="http://www.w3.org/2005/xpath-functions";

(:---------------------------------------------
 : Small helper: GET JSON with basic retry
 :---------------------------------------------)
declare function local:http-get-json($url as xs:string, $attempt as xs:integer := 1) as map(*)? {
  try {
    let $req :=
      <http:request href="{$url}" method="GET">
        <http:header name="Accept" value="application/json"/>
        <http:header name="User-Agent" value="CAB-integration/1.0 (eXist-db)"/>
      </http:request>
    let $resp := http:send-request($req)
    let $head := $resp[1]
    let $body := $resp[2]
    return
      if ($head/http:response/@status != 200) then
        if ($attempt lt 3) then local:http-get-json($url, $attempt + 1) else ()
      else
        let $mt := $head/http:body/@media-type
        return
          if ($mt = "application/json") then fn:json-to-xml($body => util:base64-decode()) else ()
  } catch * {
    if ($attempt lt 3) then local:http-get-json($url, $attempt + 1) else ()
  }
};

(:---------------------------------------------
 : Fetch all pages for a given base URL (with page_size)
 : Assumes DRF-style { "results": [...], "next": URL-or-null }
 :---------------------------------------------)
declare function local:fetch-all($url as xs:string) as element(fn:map)* {
  let $doc := local:http-get-json($url)
  let $results := $doc/fn:map/fn:array[@key="results"]/fn:map
  let $next := string($doc/fn:map/fn:string[@key="next"])
  return
    if (normalize-space($next) != "") then
      ($results, local:fetch-all($next))
    else
      $results
};

(:---------------------------------------------
 : Build the MPCD identifier *prefix* for a stanza
 : Example output (no trailing a..z):
 :   <cerem>_ch<chapter>_<section_type><stanza>_<stanza_type>
 :---------------------------------------------)
declare function local:identifier-prefix($arg_stanza as xs:string) as xs:string {
  let $first := substring-before($arg_stanza, '.')
  let $cerem := string-join(functx:get-matches($first, '[A-Z,a-z]'))
  let $chapter := string-join(functx:get-matches($first, '\d+'))
  let $stanza := functx:substring-after-last($arg_stanza, '.')
  let $section_type :=
        if (contains($arg_stanza, "Y")) then "st"
   else if (contains($arg_stanza, "VrS")) then "st"
   else if (contains($arg_stanza, "VS")) then "sec"
   else ""
  let $stanza_type :=
        if (contains($arg_stanza, "Y")) then "typtr_ln"
   else if (contains($arg_stanza, "VrS")) then "typtr_ln"
   else if (contains($arg_stanza, "VS")) then "subsec"
   else ""
  return concat($cerem, "_ch", $chapter, "_", $section_type, $stanza, "_", $stanza_type)
};

(:---------------------------------------------
 : Map CAB ceremony code (Y/VrS/VS) + numbers back to xml:id stem
 :---------------------------------------------)
declare function local:cab-id-stem($arg_stanza as xs:string) as xs:string {
  let $first := substring-before($arg_stanza, '.')
  let $cerem := string-join(functx:get-matches($first, '[A-Z,a-z]'))
  let $chapter := string-join(functx:get-matches($first, '\d+'))
  let $stanza := functx:substring-after-last($arg_stanza, '.')
  return concat($cerem, $chapter, ".", $stanza)
};

(:---------------------------------------------
 : Main stanza → Pahlavi fetcher
 :---------------------------------------------)
declare function local:getPahlavi($arg_stanza as xs:string) {
  let $prefix := local:identifier-prefix($arg_stanza)
  let $base-url := concat("https://www.mpcorpus.org/api/sections/?page_size=200&identifier=", encode-for-uri($prefix))
  let $items := local:fetch-all($base-url)

  (: If MPCD doesn't paginate and returns a flat array (no 'results'),
     comment the line above and instead use:
     let $items := local:http-get-json($base-url)/fn:map/fn:array/fn:map
  :)

  let $cab_stem := local:cab-id-stem($arg_stanza)

  return
    for $it in $items
    let $identifier := string($it/fn:string[@key="identifier"])
    (: last letter (a..z) to keep distinct xml:id per sub-stanza :)
    let $suffix := substring($identifier, string-length($identifier), 1)
    let $words := $it/fn:array[@key="words"]/fn:map/fn:string[@key="transcription"]
    where exists($words)
    order by $identifier
    return
      <div xml:id="{concat($cab_stem, $suffix)}">
        <ab>
          {
            for $w in $words
            return <w>{data($w)}</w>
          }
        </ab>
      </div>
};

(:---------------------------------------------
 : Drive over the CAB selection
 :---------------------------------------------)
for $i in collection("/db/apps/cab_tools/ur_cerem/")//text/div
return local:getPahlavi($i/@xml:id)
