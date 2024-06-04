import requests, csv, time, os.path, random

random_number = random.randrange(1000000)
csv_url = "https://candidates.democracyclub.org.uk/data/export_csv/?election_date=&ballot_paper_id=&election_id=parl.2024-07-04&party_id=&cancelled=&field_group=candidacy&field_group=person&format=csv&decache=%s" % (random_number)

request = requests.get(csv_url)
with open('2024-candidates.csv', 'wb') as file:
    file.write(request.content)

csv_file = csv.DictReader(open("2024-candidates.csv"))
for candidate in csv_file:
    person_id = candidate["person_id"]
    print("Got person %s" % (candidate["person_name"]))

    image_file = "%s.jpg" % candidate["person_id"]
    image_path = "../static/img/2024-candidates/%s" % image_file

    if os.path.isfile(image_path):
        print("Image already exists %s" % candidate["person_name"])
    else:

        if candidate.get("image"):
            image_url = candidate.get("image")

            image_response = requests.get(image_url)
            image_response.raise_for_status()

            print("Got image %s" % candidate["person_name"])

            file_name = image_path
            file = open(file_name, 'a+b')
            file.write(image_response.content)
            file.close()
            print("Wrote image %s" % candidate["person_name"])