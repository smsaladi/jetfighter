
-- total screened
SELECT COUNT(*)
    FROM `biorxiv`
    WHERE parse_status != 0;
-- detections
SELECT COUNT(*)
    FROM `biorxiv`
    WHERE parse_status > 0;
-- emails sent
SELECT COUNT(*)
    FROM `biorxiv`
    WHERE email_sent IS NOT NULL;


-- in the last 1 month
-- total screened
SELECT COUNT(*)
    FROM `biorxiv`
    WHERE created > DATE_ADD(NOW(), INTERVAL -1 MONTH)
    AND parse_status != 0;
-- detections
SELECT COUNT(*)
    FROM `biorxiv`
    WHERE created > DATE_ADD(NOW(), INTERVAL -1 MONTH)
    AND parse_status > 0;
-- emails sent
SELECT COUNT(*)
    FROM `biorxiv`
    WHERE created > DATE_ADD(NOW(), INTERVAL -1 MONTH)
    AND email_sent IS NOT NULL;
