import json
import pandas as pd
import requests

# Step 1: Define the endpoint and headers for authorization
API_URL = "https://api.opslevel.com/graphql"  # Replace with your actual API URL
AUTH_TOKEN = "<API Token>"  # Replace with your authentication token

# Define the paths for the files to be read
CHECK_ID_CSV_PATH = "/Users/tomszacharia/code/customers/flexport/custom_check_ids.csv"  # Replace with the path to your csv file with the IDs for custom checks
CHECKS_JSON_PATH = "/Users/tomszacharia/code/customers/flexport/checks_convoy.json"  # Replace with the path to your json payload containing checks

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "graphql-visibility": "internal"
}

# Step 2: Read list of IDs from the CSV file without a header

df = pd.read_csv(CHECK_ID_CSV_PATH)
filter_ids = df['id'].tolist()

# Step 3: Read JSON data from the file
with open(CHECKS_JSON_PATH, 'r') as json_file:
    json_list = json.load(json_file)

# Step 4: Filter the JSON list using the IDs from the CSV and save the names
filtered_items = []
for item in json_list:
    check_id = item.get('check', {}).get('id')
    if check_id in filter_ids:
        name = item.get('check', {}).get('name')
        filtered_items.append({
            "id": check_id,
            "name": name,
            "category_id": item.get('check', {}).get('category', {}).get('id'),
            "filter_id": item.get('check', {}).get('filter', {}).get('id'),
            "level_id": item.get('check', {}).get('level', {}).get('id')
        })
#print(filtered_items)
# Step 5: Iterate over the filtered items and make API calls
for item in filtered_items:
    # Extract necessary details
    check_id = item['id']
    name = item['name']
    category_id = item['category_id']
    filter_id = item['filter_id']
    level_id = item['level_id']
    print(name)
    #if not (category_id and filter_id and level_id):
    if not (check_id):        
        print(f"Skipping item due to missing values: {item}")
        continue

    # Step 6: Create an integration for each item
    event_integration_payload = {
        "operationName": "eventIntegrationCreate",
        "query": """
        mutation eventIntegrationCreate($type: EventIntegrationEnum!, $name: String!) {
          eventIntegrationCreate(input: {type: $type, name: $name}) {
            integration {
              id
            }
            errors {
              message
              path
            }
          }
        }
        """,
        "variables": {
            "type": "customEvent",
            "name": f"{name}-cec"  # Use the name variable for each integration
        }
    }

    response = requests.post(API_URL, headers=headers, json=event_integration_payload)

    if response.status_code == 200:
        integration_data = response.json()
        #print(response.text)
        print(f"Created integration for item with check.id {check_id}.")
        integration_id = integration_data.get("data", {}).get("eventIntegrationCreate", {}).get("integration", {}).get("id")
        if not integration_id:
            print(f"Error: Could not create integration for item with check.id {check_id}, skipping.")
            continue
        print(f"Integration ID created for item with check.id {check_id}: {integration_id}")
    else:
        print(f"Failed to create integration for item with check.id {check_id}: {response.status_code}")
        #print(response.text)
        continue

    # Step 7: Define the payload for the `checkCreation` API request
    payload = {
        "operationName": "checkCreation",
        "query": """mutation checkCreation($name: String!, $type: CheckType!, $notes: String, $ownerId: ID, $args: JSON, $filterId: ID, $levelId: ID, $categoryId: ID, $campaignId: ID, $integrationId: ID, $enabled: Boolean!, $enableOn: ISO8601DateTime) {
        checkCreate(
            input: {name: $name, type: $type, notes: $notes, ownerId: $ownerId, args: $args, filterId: $filterId, levelId: $levelId, categoryId: $categoryId, campaignId: $campaignId, integrationId: $integrationId, enabled: $enabled, enableOn: $enableOn}
        ) {
            check {
            filter {
                id
                __typename
            }
            ...BasicCheckFragment
            ...CheckStatsFragment
            __typename
            }
            errors {
            message
            path
            title
            __typename
            }
            __typename
        }
        }

        fragment BasicCheckFragment on Check {
        id
        gid: id
        name
        notes: rawNotes
        report_href: reportHref
        reportHref
        url
        owner {
            ... on Team {
            name
            href
            id
            gid: id
            __typename
            }
            ... on User {
            name
            href
            id
            gid: id
            __typename
            }
            __typename
        }
        type
        args
        enabled
        enableOn
        description
        category {
            name
            id
            gid: id
            __typename
        }
        checkLevels {
            level {
            name
            index
            id
            gid: id
            __typename
            }
            __typename
        }
        filter {
            name
            id
            gid: id
            path
            __typename
        }
        integration {
            ...IntegrationWithCheckCreateTemplateConfigFragment
            __typename
        }
        container {
            permissions {
            canUpdate
            __typename
            }
            __typename
        }
        __typename
        }

        fragment IntegrationWithCheckCreateTemplateConfigFragment on Integration {
        ...BasicIntegrationFragment
        gid: id
        webhookUrl
        htmlUrl
        valid
        active
        config {
            checkCreateTemplates {
            defaultName
            resultMessage
            samplePayload
            sampleQueryParams
            serviceSpecifier
            successCondition
            passPending
            __typename
            }
            __typename
        }
        __typename
        }

        fragment BasicIntegrationFragment on Integration {
        id
        name
        shortName
        type
        accountKey
        notificationChannel
        setWebhooksOnMonitors
        baseUrl
        ignoredPatterns
        href
        serviceDiscoveryEnabled
        earlyAccess
        warnings {
            id
            message
            createdAt
            dismissed
            __typename
        }
        ... on ManualAlertSourceSync {
            lastManualSyncAlertSources
            allowManualSyncAlertSources
            __typename
        }
        ... on AzureDevopsIntegration {
            permissionsErrors {
            name
            type
            permissions
            __typename
            }
            accountErrors
            __typename
        }
        ... on AzureResourcesIntegration {
            tenantId
            subscriptionId
            lastSyncedAt
            aliases
            allowManualSyncInfrastructureResources
            minutesUntilManualSyncInfrastructureResourcesAllowed
            __typename
        }
        ... on SonarqubeCloudIntegration {
            organizationKey
            __typename
        }
        __typename
        }

        fragment CheckStatsFragment on Check {
        stats {
            total
            totalSuccessful
            __typename
        }
        __typename
        }""",
        "variables": {
            "args": {
                "jq": ".status == \"passed\"",
                "pass_pending": True,
                "payload": {
                    "check": "checkReferenceId",
                    "message": "You shall not pass!!",
                    "service": "serviceAlias",
                    "status": "failed"
                },
                "query_params": "alias=serviceAlias",
                "result_msg": "{% if check.passed %}\n  ### Check passed\n{% else %}\n  ### Check failed\n  Service **{{ data.service }}** failed check.\n{% endif %}\n  OpsLevel note: here you can fill in more details about this check. You can even include `data` from the payload, `params` specified in the URL and context `ctx` such as the service alias for the current evaluation.\n",
                "service_selector": ".service"
            },
            "categoryId": category_id,
            "enabled": False,
            "enableOn": None,
            "filterId": filter_id,
            "integrationId": integration_id,
            "levelId": level_id,
            "name": name,
            "notes": f"Requires a check integration API call to complete a check for the service {name}.",
            "ownerId": None,
            "type": "generic"
        }
    }

    # Step 8: Make the request to create the check
    response = requests.post(API_URL, headers=headers, json=payload)

    # Check the response
    if response.status_code == 200:
        #print(f"Response for {check_id}:", response.json())
        print(f"Check, {check_id}: created successfully for {name}")
    else:
        print(f"Failed request for {check_id}: {response.status_code}")
        print(response.text)