import pytest
from io import StringIO
from unittest.mock import patch, call, AsyncMock

from django.core.management import call_command

from givefood.models import Place


@pytest.mark.django_db
class TestPlacePopulationsCommand:
    """Tests for the place_populations management command."""

    def _create_place(self, gbpnid, name, population=None, **kwargs):
        """Helper to create a Place for testing."""
        defaults = {
            "gbpnid": gbpnid,
            "name": name,
            "lat_lng": "51.5074,-0.1278",
            "histcounty": "Middlesex",
            "adcounty": "Greater London",
            "district": "Westminster",
            "uniauth": "Westminster",
            "police": "Metropolitan Police",
            "region": "England",
            "type": "City",
            "population": population,
        }
        defaults.update(kwargs)
        return Place.objects.create(**defaults)

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_populates_place_without_population(self, mock_gemini):
        """Test that a place without population gets populated."""
        self._create_place(1, "Test Town")
        mock_gemini.return_value = {"population": 5000}

        out = StringIO()
        call_command('place_populations', stdout=out)

        place = Place.objects.get(gbpnid=1)
        assert place.population == 5000
        assert mock_gemini.called
        assert "Test Town: 5000" in out.getvalue()

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_skips_place_with_existing_population(self, mock_gemini):
        """Test that places with existing population are skipped."""
        self._create_place(1, "Existing Town", population=10000)

        out = StringIO()
        call_command('place_populations', stdout=out)

        assert not mock_gemini.called
        assert "Found 0 places without population" in out.getvalue()

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_skips_place_with_zero_population(self, mock_gemini):
        """Test that places with zero population are skipped."""
        self._create_place(1, "Zero Town", population=0)

        out = StringIO()
        call_command('place_populations', stdout=out)

        assert not mock_gemini.called
        assert "Found 0 places without population" in out.getvalue()

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_populates_multiple_places(self, mock_gemini):
        """Test that multiple places get populated."""
        self._create_place(1, "Town A")
        self._create_place(2, "Town B")

        mock_gemini.side_effect = [
            {"population": 1000},
            {"population": 2000},
        ]

        out = StringIO()
        call_command('place_populations', stdout=out)

        populations = set(Place.objects.values_list("population", flat=True))
        assert populations == {1000, 2000}
        assert mock_gemini.call_count == 2

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_only_populates_null_population(self, mock_gemini):
        """Test that only places with null population are processed."""
        self._create_place(1, "Has Pop", population=500)
        self._create_place(2, "No Pop")

        mock_gemini.return_value = {"population": 3000}

        out = StringIO()
        call_command('place_populations', stdout=out)

        assert mock_gemini.call_count == 1
        assert Place.objects.get(gbpnid=1).population == 500
        assert Place.objects.get(gbpnid=2).population == 3000

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_population_can_be_zero(self, mock_gemini):
        """Test that AI can return zero population."""
        self._create_place(1, "Ghost Town")

        mock_gemini.return_value = {"population": 0}

        out = StringIO()
        call_command('place_populations', stdout=out)

        place = Place.objects.get(gbpnid=1)
        assert place.population == 0
        assert "Ghost Town: 0" in out.getvalue()

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_prompt_includes_all_fields(self, mock_gemini):
        """Test that the prompt includes all place fields."""
        self._create_place(
            1, "Detail Town",
            lat_lng="52.0,-1.0",
            histcounty="Warwickshire",
            adcounty="West Midlands",
            district="Birmingham",
            uniauth="Birmingham",
            police="West Midlands Police",
            region="England",
            type="City",
        )

        mock_gemini.return_value = {"population": 1000000}

        call_command('place_populations')

        prompt = mock_gemini.call_args[1]["prompt"]
        assert "Detail Town" in prompt
        assert "52.0,-1.0" in prompt
        assert "Warwickshire" in prompt
        assert "West Midlands" in prompt
        assert "Birmingham" in prompt
        assert "West Midlands Police" in prompt
        assert "England" in prompt
        assert "City" in prompt

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_gemini_called_with_correct_params(self, mock_gemini):
        """Test that gemini is called with the correct parameters."""
        self._create_place(1, "Param Town")
        mock_gemini.return_value = {"population": 100}

        call_command('place_populations')

        call_kwargs = mock_gemini.call_args[1]
        assert call_kwargs["temperature"] == 0
        assert call_kwargs["response_mime_type"] == "application/json"
        assert "population" in call_kwargs["response_schema"]["properties"]
        assert call_kwargs["response_schema"]["properties"]["population"]["type"] == "integer"

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_output_shows_count(self, mock_gemini):
        """Test that the output shows the count of places."""
        self._create_place(1, "Town A")
        self._create_place(2, "Town B")

        mock_gemini.side_effect = [
            {"population": 100},
            {"population": 200},
        ]

        out = StringIO()
        call_command('place_populations', stdout=out)

        assert "Found 2 places without population" in out.getvalue()

    @patch('gfoffline.management.commands.place_populations.gemini_async', new_callable=AsyncMock)
    def test_batching(self, mock_gemini):
        """Test that places are processed in batches."""
        for i in range(15):
            self._create_place(i + 1, f"Town {i + 1}")

        mock_gemini.side_effect = [{"population": i * 100} for i in range(15)]

        out = StringIO()
        call_command('place_populations', stdout=out)

        assert mock_gemini.call_count == 15
        assert Place.objects.filter(population__isnull=False).count() == 15
