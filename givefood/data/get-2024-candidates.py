import requests, csv, time, os.path

csv_url = "https://candidates.democracyclub.org.uk/data/export_csv/?election_date=&ballot_paper_id=&election_id=parl.2024-07-04&party_id=&cancelled=&field_group=candidacy&field_group=person&format=csv"

request = requests.get(csv_url)
with open('2024-candidates.csv', 'wb') as file:
    file.write(request.content)

csv_file = csv.DictReader(open("2024-candidates.csv"))
for candidate in csv_file:
    person_id = candidate["person_id"]
    print("Got person %s" % (candidate["person_name"]))

    if os.path.isfile("../static/img/2024-candidates/%s.jpg" % candidate["person_id"]):
        print("Image already exists %s" % candidate["person_name"])
    else:

        if candidate.get("image"):
            image_url = candidate.get("image")

            image_response = requests.get(image_url)
            image_response.raise_for_status()

            print("Got image %s" % candidate["person_name"])

            file_name = "../static/img/2024-candidates/%s.jpg" % candidate["person_id"]
            file = open(file_name, 'a+b')
            file.write(image_response.content)
            file.close()
            print("Wrote image %s" % candidate["person_name"])
        # time.sleep(2)

        # api_url = "https://candidates.democracyclub.org.uk/api/next/people/%s/" % (person_id)
        # request = requests.get(api_url)
        # request.raise_for_status()
        # person = request.json()
        # if person.get("thumbnail"):
        #     image_url = person.get("thumbnail")

        #     image_response = requests.get(image_url)
        #     image_response.raise_for_status()

        #     print("Got image %s" % candidate["person_name"])

        #     file_name = "../static/img/2024-candidates/%s.jpg" % candidate["person_id"]
        #     file = open(file_name, 'a+b')
        #     file.write(image_response.content)
        #     file.close()