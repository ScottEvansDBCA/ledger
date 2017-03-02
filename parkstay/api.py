import traceback
import base64
import geojson
from six.moves.urllib.parse import urlparse
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from rest_framework import viewsets, serializers, status, generics, views
from rest_framework.decorators import detail_route, list_route
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission
from rest_framework.pagination import PageNumberPagination
from datetime import datetime, timedelta
from collections import OrderedDict
from django.core.cache import cache
from ledger.accounts.models import EmailUser,Address
from parkstay import utils
from datetime import datetime,timedelta, date
from parkstay.models import (Campground,
                                CampsiteBooking,
                                Campsite,
                                CampsiteRate,
                                Booking,
                                CampgroundBookingRange,
                                CampsiteBookingRange,
                                CampsiteStayHistory,
                                CampgroundStayHistory,
                                PromoArea,
                                Park,
                                Feature,
                                Region,
                                CampsiteClass,
                                Booking,
                                CampsiteRate,
                                Rate,
                                CampgroundPriceHistory,
                                CampsiteClassPriceHistory,
                                ClosureReason,
                                OpenReason,
                                PriceReason,
                                MaximumStayReason,
                                ParkEntryRate,
                                )

from parkstay.serialisers import (  CampsiteBookingSerialiser,
                                    CampsiteSerialiser,
                                    CampgroundMapSerializer,
                                    CampgroundMapFilterSerializer,
                                    CampgroundSerializer,
                                    CampgroundCampsiteFilterSerializer,
                                    CampsiteBookingSerializer,
                                    PromoAreaSerializer,
                                    ParkSerializer,
                                    FeatureSerializer,
                                    RegionSerializer,
                                    CampsiteClassSerializer,
                                    BookingSerializer,
                                    CampgroundBookingRangeSerializer,
                                    CampsiteBookingRangeSerializer,
                                    CampsiteRateSerializer,
                                    CampsiteRateReadonlySerializer,
                                    CampsiteStayHistorySerializer,
                                    CampgroundStayHistorySerializer,
                                    RateSerializer,
                                    RateDetailSerializer,
                                    CampgroundPriceHistorySerializer,
                                    CampsiteClassPriceHistorySerializer,
                                    CampgroundImageSerializer,
                                    ExistingCampgroundImageSerializer,
                                    ClosureReasonSerializer,
                                    OpenReasonSerializer,
                                    PriceReasonSerializer,
                                    MaximumStayReasonSerializer,
                                    BulkPricingSerializer,
                                    UsersSerializer,
                                    AccountsAddressSerializer,
                                    ParkEntryRateSerializer,
                                    )
from parkstay.helpers import is_officer, is_customer



# API Views
class CampsiteBookingViewSet(viewsets.ModelViewSet):
    queryset = CampsiteBooking.objects.all()
    serializer_class = CampsiteBookingSerialiser


class CampsiteViewSet(viewsets.ModelViewSet):
    queryset = Campsite.objects.all()
    serializer_class = CampsiteSerialiser


    def list(self, request, format=None):
        queryset = self.get_queryset()
        formatted = bool(request.GET.get("formatted", False))
        serializer = self.get_serializer(queryset, formatted=formatted, many=True, method='get')
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        formatted = bool(request.GET.get("formatted", False))
        serializer = self.get_serializer(instance, formatted=formatted, method='get')
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance,data=request.data,partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def create(self, request, *args, **kwargs):
        try:
            http_status = status.HTTP_200_OK
            number = request.data.pop('number')
            serializer = self.get_serializer(data=request.data,method='post')
            serializer.is_valid(raise_exception=True)

            if number >  1:
                data = dict(serializer.validated_data)
                campsites = Campsite.bulk_create(number,data)
                res = self.get_serializer(campsites,many=True)
            else:
                if number == 1 and serializer.validated_data['name'] == 'default':
                    latest = 0
                    current_campsites = Campsite.objects.filter(campground=serializer.validated_data.get('campground'))
                    cs_numbers = [int(c.name) for c in current_campsites if c.name.isdigit()]
                    if cs_numbers:
                        latest = max(cs_numbers)
                    if len(str(latest+1)) == 1:
                        name = '0{}'.format(latest+1)
                    else:
                        name = str(latest+1)
                    serializer.validated_data['name'] = name
                instance = serializer.save()
                res = self.get_serializer(instance)

            return Response(res.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    def open_close(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            # parse and validate data
            mutable = request.POST._mutable
            request.POST._mutable = True
            request.POST['campsite'] = self.get_object().id
            request.POST._mutable = mutable
            serializer = CampsiteBookingRangeSerializer(data=request.data, method="post")
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data.get('status') == 0:
                self.get_object().open(dict(serializer.validated_data))
            else:
                self.get_object().close(dict(serializer.validated_data))

            # return object
            ground = self.get_object()
            res = CampsiteSerialiser(ground, context={'request':request})

            return Response(res.data)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def status_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            # Check what status is required
            closures = bool(request.GET.get("closures", False))
            if closures:
                serializer = CampsiteBookingRangeSerializer(self.get_object().booking_ranges.filter(~Q(status=0)),many=True)
            else:
                serializer = CampsiteBookingRangeSerializer(self.get_object().booking_ranges,many=True)
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def stay_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            serializer = CampsiteStayHistorySerializer(self.get_object().stay_history,many=True,context={'request':request},method='get')
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def price_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            price_history = self.get_object().rates.all().order_by('-date_start')
            serializer = CampsiteRateReadonlySerializer(price_history,many=True,context={'request':request})
            res = serializer.data
            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

class CampsiteStayHistoryViewSet(viewsets.ModelViewSet):
    queryset = CampsiteStayHistory.objects.all()
    serializer_class = CampsiteStayHistorySerializer

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if instance.range_end and not serializer.validated_data.get('range_end'):
                instance.range_end = None
            self.perform_update(serializer)

            return Response(serializer.data)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

class CampgroundStayHistoryViewSet(viewsets.ModelViewSet):
    queryset = CampgroundStayHistory.objects.all()
    serializer_class = CampgroundStayHistorySerializer

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if instance.range_end and not serializer.validated_data.get('range_end'):
                instance.range_end = None
            self.perform_update(serializer)

            return Response(serializer.data)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))


class CampgroundMapViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campground.objects.all()
    serializer_class = CampgroundMapSerializer
    permission_classes = []


class CampgroundMapFilterViewSet(viewsets.ReadOnlyModelViewSet):
    # TODO: add exclude for unpublished campground objects
    #queryset = Campground.objects.exclude(campground_type=1)
    queryset = Campground.objects.all()
    serializer_class = CampgroundMapFilterSerializer
    permission_classes = []


    def list(self, request, *args, **kwargs):
        print(request.GET)
        data = {
            "arrival" : request.GET.get('arrival', None),
            "departure" : request.GET.get('departure', None),
            "num_adult" : request.GET.get('num_adult', 0),
            "num_concession" : request.GET.get('num_concession', 0),
            "num_child" : request.GET.get('num_child', 0),
            "num_infant" : request.GET.get('num_infant', 0),
            "gear_type": request.GET.get('gear_type', 'tent')
        }

        serializer = CampgroundCampsiteFilterSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        scrubbed = serializer.validated_data
        if scrubbed['arrival'] and scrubbed['departure'] and (scrubbed['arrival'] < scrubbed['departure']):
            sites = Campsite.objects.filter(**{scrubbed['gear_type']: True})
            ground_ids = utils.get_open_campgrounds(sites, scrubbed['arrival'], scrubbed['departure'])

        else:
            ground_ids = set((x[0] for x in Campsite.objects.filter(**{scrubbed['gear_type']: True}).values_list('campground')))
        

        # we need to be tricky here. for the default search (tent, any timestamps)
        # we want to include all of the "campgrounds" that don't have any campsites in the model! (i.e. non-P&W)
        if scrubbed['gear_type'] == 'tent':
            ground_ids.update((x[0] for x in Campground.objects.filter(campsites__isnull=True).values_list('id')))

        queryset = Campground.objects.filter(id__in=ground_ids).order_by('name')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


def search_suggest(request, *args, **kwargs):
    entries = []
    for x in Campground.objects.filter(wkb_geometry__isnull=False).values_list('id', 'name', 'wkb_geometry'):
        entries.append(geojson.Point((x[2].x, x[2].y), properties={'type': 'Campground', 'id': x[0], 'name': x[1]}))
    for x in Park.objects.filter(wkb_geometry__isnull=False).values_list('id', 'name', 'wkb_geometry'):
        entries.append(geojson.Point((x[2].x, x[2].y), properties={'type': 'Park', 'id': x[0], 'name': x[1]}))
    for x in PromoArea.objects.filter(wkb_geometry__isnull=False).values_list('id', 'name', 'wkb_geometry'):
        entries.append(geojson.Point((x[2].x, x[2].y), properties={'type': 'PromoArea', 'id': x[0], 'name': x[1]}))

    return HttpResponse(geojson.dumps(geojson.FeatureCollection(entries)), content_type='application/json')


class CampgroundViewSet(viewsets.ModelViewSet):
    queryset = Campground.objects.all()
    serializer_class = CampgroundSerializer


    def list(self, request, format=None):

        data = cache.get('campgrounds')
        if data is None:
            queryset = self.get_queryset()
            formatted = bool(request.GET.get("formatted", False))
            serializer = self.get_serializer(queryset, formatted=formatted, many=True, method='get')
            data = serializer.data
            cache.set('campgrounds',data,3600)
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        formatted = bool(request.GET.get("formatted", False))
        serializer = self.get_serializer(instance, formatted=formatted, method='get')
        return Response(serializer.data)

    def strip_b64_header(self, content):
        if ';base64,' in content:
            header, base64_data = content.split(';base64,')
            return base64_data
        return content

    def create(self, request, format=None):
        try:
            images_data = None
            http_status = status.HTTP_200_OK
            if "images" in request.data:
                images_data = request.data.pop("images")
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance =serializer.save()
            # Get and Validate campground images
            initial_image_serializers = [CampgroundImageSerializer(data=image) for image in images_data] if images_data else []
            image_serializers = []
            if initial_image_serializers:

                for image_serializer in initial_image_serializers:
                    result = urlparse(image_serializer.initial_data['image'])
                    if not (result.scheme =='http' or result.scheme == 'https') and not result.netloc:
                        image_serializers.append(image_serializer)

                if image_serializers:
                    for image_serializer in image_serializers:
                        image_serializer.initial_data["campground"] = instance.id
                        image_serializer.initial_data["image"] = ContentFile(base64.b64decode(self.strip_b64_header(image_serializer.initial_data["image"])))
                        image_serializer.initial_data["image"].name = 'uploaded'

                    for image_serializer in image_serializers:
                        image_serializer.is_valid(raise_exception=True)

                    for image_serializer in image_serializers:
                        image_serializer.save()

            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        try:
            images_data = None
            http_status = status.HTTP_200_OK
            instance = self.get_object()
            if "images" in request.data:
                images_data = request.data.pop("images")
            serializer = self.get_serializer(instance,data=request.data,partial=True)
            serializer.is_valid(raise_exception=True)
            # Get and Validate campground images
            initial_image_serializers = [CampgroundImageSerializer(data=image) for image in images_data] if images_data else []
            image_serializers, existing_image_serializers = [],[]
            # Get campgrounds current images
            current_images = instance.images.all()
            if initial_image_serializers:

                for image_serializer in initial_image_serializers:
                    result = urlparse(image_serializer.initial_data['image'])
                    if not (result.scheme =='http' or result.scheme == 'https') and not result.netloc:
                        image_serializers.append(image_serializer)
                    else:
                        data = {
                            'id':image_serializer.initial_data['id'],
                            'image':image_serializer.initial_data['image'],
                            'campground':instance.id
                        }
                        existing_image_serializers.append(ExistingCampgroundImageSerializer(data=data))

                # Dealing with existing images
                images_id_list = []
                for image_serializer in existing_image_serializers:
                    image_serializer.is_valid(raise_exception=True)
                    images_id_list.append(image_serializer.validated_data['id'])

                #Get current object images and check if any has been removed
                for img in current_images:
                    if img.id not in images_id_list:
                        img.delete()

                # Creating new Images
                if image_serializers:
                    for image_serializer in image_serializers:
                        image_serializer.initial_data["campground"] = instance.id
                        image_serializer.initial_data["image"] = ContentFile(base64.b64decode(self.strip_b64_header(image_serializer.initial_data["image"])))
                        image_serializer.initial_data["image"].name = 'uploaded'

                    for image_serializer in image_serializers:
                        image_serializer.is_valid(raise_exception=True)

                    for image_serializer in image_serializers:
                        image_serializer.save()
            else:
                if current_images:
                    current_images.delete()

            self.perform_update(serializer)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'])
    def open_close(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            # parse and validate data
            mutable = request.POST._mutable
            request.POST._mutable = True
            request.POST['campground'] = self.get_object().id
            request.POST._mutable = mutable
            serializer = CampgroundBookingRangeSerializer(data=request.data, method="post")
            serializer.is_valid(raise_exception=True)
            if serializer.validated_data.get('status') == 0:
                self.get_object().open(dict(serializer.validated_data))
            else:
                self.get_object().close(dict(serializer.validated_data))

            # return object
            ground = self.get_object()
            res = CampgroundSerializer(ground, context={'request':request})

            return Response(res.data)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'],)
    def addPrice(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            rate = None
            serializer = RateDetailSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            rate_id = serializer.validated_data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=serializer.validated_data['adult'],concession=serializer.validated_data['concession'],child=serializer.validated_data['child'],infant=serializer.validated_data['infant'])[0]
            if rate:
                serializer.validated_data['rate']= rate
                data = {
                    'rate': rate,
                    'date_start': serializer.validated_data['period_start'],
                    'reason': PriceReason.objects.get(pk = serializer.validated_data['reason']),
                    'details': serializer.validated_data['details'],
                    'update_level': 0
                }
                self.get_object().createCampsitePriceHistory(data)
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id)
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.format_exc())
            raise
        except Exception as e:
            print(traceback.format_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'],)
    def updatePrice(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            original_data = request.data.pop('original')
            original_serializer = CampgroundPriceHistorySerializer(data=original_data,method='post')
            original_serializer.is_valid(raise_exception=True)

            serializer = RateDetailSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            rate_id = serializer.validated_data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=serializer.validated_data['adult'],concession=serializer.validated_data['concession'],child=serializer.validated_data['child'],infant=serializer.validated_data['infant'])[0]
            if rate:
                serializer.validated_data['rate']= rate
                new_data = {
                    'rate': rate,
                    'date_start': serializer.validated_data['period_start'],
                    'reason': PriceReason.objects.get(pk=serializer.validated_data['reason']),
                    'details': serializer.validated_data['details'],
                    'update_level': 0
                }
                self.get_object().updatePriceHistory(dict(original_serializer.validated_data),new_data)
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id)
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'],)
    def deletePrice(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            serializer = CampgroundPriceHistorySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            self.get_object().deletePriceHistory(serializer.validated_data)
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id)
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def status_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            # Check what status is required
            closures = bool(request.GET.get("closures", False))
            if closures:
                serializer = CampgroundBookingRangeSerializer(self.get_object().booking_ranges.filter(~Q(status=0)),many=True)
            else:
                serializer = CampgroundBookingRangeSerializer(self.get_object().booking_ranges,many=True)
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def campsites(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            serializer = CampsiteSerialiser(self.get_object().campsites,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def price_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id).order_by('-date_start')
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def current_price(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK

            start_date = request.GET.get('arrival',False)
            end_date = request.GET.get('departure',False)
            res = []
            if start_date and end_date:
                start_date = datetime.strptime(start_date,"%Y-%m-%d").date()
                end_date = datetime.strptime(end_date,"%Y-%m-%d").date()
                for single_date in utils.daterange(start_date, end_date):
                    price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id,date_start__lte=single_date).order_by('-date_start')
                    if price_history:
                        serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
                        res.append({
                            "date" : single_date.strftime("%Y-%m-%d") ,
                            "rate" : serializer.data[0]
                        })
                    else:
                        res.append({
                            "error":"There is no park entry set",
                            "success":False
                        })
            else:
                res.append({
                    "error":"Arrival and departure dates are required",
                    "success":False
                })

            return Response(res,status=http_status)
        except serializers.ValidationError:
            traceback.print_exc()
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['get'])
    def stay_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            start = request.GET.get("start",False)
            end = request.GET.get("end",False)
            serializer = None
            if (start) or (end):
                start = datetime.strptime(start,"%Y-%m-%d").date()
                end = datetime.strptime(end,"%Y-%m-%d").date()
                queryset = CampgroundStayHistory.objects.filter(range_end__range = (start,end), range_start__range=(start,end) ).order_by("range_start")[:5]
                serializer = CampgroundStayHistorySerializer(queryset,many=True,context={'request':request},method='get')
            else:
                serializer = CampgroundStayHistorySerializer(self.get_object().stay_history,many=True,context={'request':request},method='get')
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))


    @detail_route(methods=['get'])
    def available_campsites(self, request, format='json', pk=None):
        try:
            start_date = datetime.strptime(request.GET.get('arrival'),'%Y/%m/%d').date()
            end_date = datetime.strptime(request.GET.get('departure'),'%Y/%m/%d').date()
            campsite_qs = Campsite.objects.all().filter(campground_id=self.get_object().id)
            http_status = status.HTTP_200_OK
            available = utils.get_available_campsites_list(campsite_qs,request, start_date, end_date)

            return Response(available,status=http_status)
        except Exception as e:
            raise serializers.ValidationError(str(e))



class AvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Campground.objects.all()
    serializer_class = CampgroundSerializer
    permission_classes = []

    def retrieve(self, request, pk=None, format=None):
        """Fetch full campsite availability for a campground."""
        # convert GET parameters to objects
        ground = self.get_object()
        # Validate parameters
        data = {
            "arrival" : request.GET.get('arrival'),
            "departure" : request.GET.get('departure'),
            "num_adult" : request.GET.get('num_adult', 0),
            "num_concession" : request.GET.get('num_concession', 0),
            "num_child" : request.GET.get('num_child', 0),
            "num_infant" : request.GET.get('num_infant', 0),
            "gear_type" : request.GET.get('gear_type', 'tent')
        }
        serializer = CampgroundCampsiteFilterSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data['arrival']
        end_date = serializer.validated_data['departure']
        num_adult = serializer.validated_data['num_adult']
        num_concession = serializer.validated_data['num_concession']
        num_child = serializer.validated_data['num_child']
        num_infant = serializer.validated_data['num_infant']
        gear_type = serializer.validated_data['gear_type']

        # if campground doesn't support online bookings, abort!
        if ground.campground_type != 0:
            return Response({'error': 'Campground doesn\'t support online bookings'}, status=400)

        # get a length of the stay (in days), capped if necessary to the request maximum
        length = max(0, (end_date-start_date).days)
        if length > settings.PS_MAX_BOOKING_LENGTH:
            length = settings.PS_MAX_BOOKING_LENGTH
            end_date = start_date+timedelta(days=settings.PS_MAX_BOOKING_LENGTH)

        # fetch all the campsites and applicable rates for the campground
        sites_qs = Campsite.objects.filter(campground=ground).filter(**{gear_type: True})

        # fetch rate map
        rates = {
            siteid: {
                date: num_adult*info['adult']+num_concession*info['concession']+num_child*info['child']+num_infant*info['infant']
                for date, info in dates.items()
            } for siteid, dates in utils.get_visit_rates(sites_qs, start_date, end_date).items()
        }

        # fetch availability map
        availability = utils.get_campsite_availability(sites_qs, start_date, end_date)

        # create our result object, which will be returned as JSON
        result = {
            'arrival': start_date.strftime('%Y/%m/%d'),
            'days': length,
            'adults': 1,
            'children': 0,
            'maxAdults': 30,
            'maxChildren': 30,
            'sites': [],
            'classes': {}
        }

        # group results by campsite class
        if ground.site_type == 1:
            # from our campsite queryset, generate a distinct list of campsite classes
            classes = [x for x in sites_qs.distinct('campsite_class__name').order_by('campsite_class__name').values_list('pk', 'campsite_class', 'campsite_class__name')]

            classes_map = {}
            bookings_map = {}

            # create a rough mapping of rates to campsite classes
            # (it doesn't matter if this isn't a perfect match, the correct
            # pricing will show up on the booking page)
            rates_map = {}

            class_sites_map = {}
            for s in sites_qs:
                if s.campsite_class.pk not in class_sites_map:
                    class_sites_map[s.campsite_class.pk] = set()
                    rates_map[s.campsite_class.pk] = rates[s.pk]

                class_sites_map[s.campsite_class.pk].add(s.pk)


            # make an entry under sites for each campsite class
            for c in classes:
                rate = rates_map[c[1]]
                site = {
                    'name': c[2],
                    'id': None,
                    'type': c[1],
                    'price': '${}'.format(sum(rate.values())),
                    'availability': [[True, '${}'.format(rate[start_date+timedelta(days=i)]), rate[start_date+timedelta(days=i)], [0, 0]] for i in range(length)],
                    'breakdown': OrderedDict()
                }
                result['sites'].append(site)
                classes_map[c[1]] = site

            # make a map of class IDs to site IDs
            for s in sites_qs:
                rate = rates_map[s.campsite_class.pk]
                classes_map[s.campsite_class.pk]['breakdown'][s.name] = [[True, '${}'.format(rate[start_date+timedelta(days=i)]), rate[start_date+timedelta(days=i)]] for i in range(length)]

            # store number of campsites in each class
            class_sizes = {k: len(v) for k, v in class_sites_map.items()}

            # update results based on availability map
            for s in sites_qs:
                # get campsite class key
                key = s.campsite_class.pk
                # if there's not a free run of slots
                if not all([v[0] == 'open' for k, v in availability[s.pk].items()]):
                    # clear the campsite from the campsite class map
                    if s.pk in class_sites_map[key]:
                        class_sites_map[key].remove(s.pk)

                    # update the days that are non-open
                    for offset, stat in [((k-start_date).days, v[0]) for k, v in availability[s.pk].items() if v[0] != 'open']:
                        # update the per-site availability
                        classes_map[key]['breakdown'][s.name][offset][0] = False
                        classes_map[key]['breakdown'][s.name][offset][1] = 'Closed' if (stat == 'closed') else 'Sold'

                        # update the class availability status
                        book_offset = 1 if (stat == 'closed') else 0
                        classes_map[key]['availability'][offset][3][book_offset] += 1
                        if classes_map[key]['availability'][offset][3][0] == class_sizes[key]:
                            classes_map[key]['availability'][offset][1] = 'Fully Booked'
                        elif classes_map[key]['availability'][offset][3][1] == class_sizes[key]:
                            classes_map[key]['availability'][offset][1] = 'Closed'
                        elif classes_map[key]['availability'][offset][3][0] >= classes_map[key]['availability'][offset][3][1]:
                            classes_map[key]['availability'][offset][1] = 'Partially Booked'
                        else:
                            classes_map[key]['availability'][offset][1] = 'Partially Closed'

                        # tentatively flag campsite class as unavailable
                        classes_map[key]['availability'][offset][0] = False
                        classes_map[key]['price'] = False

            # convert breakdowns to a flat list
            for klass in classes_map.values():
                klass['breakdown'] = [{'name': k, 'availability': v} for k, v in klass['breakdown'].items()]

            # any campsites remaining in the class sites map have zero bookings!
            # check if there's any left for each class, and if so return that as the target
            for k, v in class_sites_map.items():
                if v:
                    rate = rates_map[k]
                    classes_map[k].update({
                        'id': v.pop(),
                        'price': '${}'.format(sum(rate.values())),
                        'availability': [[True, '${}'.format(rate[start_date+timedelta(days=i)]), rate[start_date+timedelta(days=i)], [0, 0]] for i in range(length)],
                        'breakdown': []
                    })


            return Response(result)


        # don't group by class, list individual sites
        else:
            # from our campsite queryset, generate a digest for each site
            sites_map = OrderedDict([(s.name, (s.pk, s.campsite_class, rates[s.pk])) for s in sites_qs])
            bookings_map = {}

            # make an entry under sites for each site
            for k, v in sites_map.items():
                site = {
                    'name': k,
                    'id': v[0],
                    'type': ground.campground_type,
                    'class': v[1].pk,
                    'price': '${}'.format(sum(v[2].values())),
                    'availability': [[True, '${}'.format(v[2][start_date+timedelta(days=i)]), v[2][start_date+timedelta(days=i)]] for i in range(length)]
                }
                result['sites'].append(site)
                bookings_map[k] = site
                if v[1].pk not in result['classes']:
                    result['classes'][v[1].pk] = v[1].name


            # update results based on availability map
            for s in sites_qs:
                # if there's not a free run of slots
                if not all([v[0] == 'open' for k, v in availability[s.pk].items()]):
                    # update the days that are non-open
                    for offset, stat in [((k-start_date).days, v[0]) for k, v in availability[s.pk].items() if v[0] != 'open']:
                        bookings_map[s.name]['availability'][offset][0] = False
                        bookings_map[s.name]['availability'][offset][1] = 'Closed' if (stat == 'closed') else 'Sold'
                        bookings_map[s.name]['price'] = False

            return Response(result)


@require_http_methods(['POST'])
def create_booking(request, *args, **kwargs):
    """Create a temporary booking and link it to the current session"""

    data = {
        'arrival': request.POST.get('arrival'),
        'departure': request.POST.get('departure'),
        'num_adult': request.POST.get('num_adult', 0),
        'num_concession': request.POST.get('num_concession', 0),
        'num_child': request.POST.get('num_child', 0),
        'num_infant': request.POST.get('num_infant', 0),
        'campground': request.POST.get('campground', 0),
        'campsite_class': request.POST.get('campsite_class', 0),
        'campsite': request.POST.get('campsite', 0)
    }

    serializer = CampsiteBookingSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    campground = serializer.validated_data['campground']
    campsite_class = serializer.validated_data['campsite_class']
    campsite = serializer.validated_data['campsite']
    start_date = serializer.validated_data['arrival']
    end_date = serializer.validated_data['departure']
    num_adult = serializer.validated_data['num_adult']
    num_concession = serializer.validated_data['num_concession']
    num_child = serializer.validated_data['num_child']
    num_infant = serializer.validated_data['num_infant']

    if 'ps_booking' in request.session:
        # if there's already a booking in the current session, send bounce signal
        messages.success(request, 'Booking already in progress, complete this first!')
        return HttpResponse(geojson.dumps({
            'status': 'success',
            'msg': 'Booking already in progress',
            'pk': request.session['ps_booking']
        }), content_type='application/json')

    # for a manually-specified campsite, do a sanity check 
    # ensure that the campground supports per-site bookings and bomb out if it doesn't
    if campsite:
        campsite_obj = Campsite.objects.prefetch_related('campground').get(pk=campsite)
        if campsite_obj.campground.site_type != 0:
            return HttpResponse(geojson.dumps({
                'status': 'error',
                'msg': 'Campground doesn\'t support per-site bookings'
            }), status=400, content_type='application/json')
    # for the rest, check that both campsite_class and campground are provided
    elif (not campsite_class) or (not campground):
        return HttpResponse(geojson.dumps({
            'status': 'error',
            'msg': 'Must specify campsite_class and campground'
        }), status=400, content_type='application/json')

    # try to create a temporary booking
    try:
        if campsite:
            booking = utils.create_booking_by_site(
                campsite, start_date, end_date,
                num_adult, num_concession,
                num_child, num_infant
            )
        else:
            booking = utils.create_booking_by_class(
                campground, campsite_class,
                start_date, end_date,
                num_adult, num_concession,
                num_child, num_infant
            )
    except ValidationError as e:
        return HttpResponse(geojson.dumps({
            'status': 'error',
            'msg': e.message
        }), status=400, content_type='application/json')

    # add the booking to the current session
    request.session['ps_booking'] = booking.pk

    return HttpResponse(geojson.dumps({
        'status': 'success',
        'pk': booking.pk
    }), content_type='application/json')


class PromoAreaViewSet(viewsets.ModelViewSet):
    queryset = PromoArea.objects.all()
    serializer_class = PromoAreaSerializer

class ParkViewSet(viewsets.ModelViewSet):
    queryset = Park.objects.all()
    serializer_class = ParkSerializer

    def list(self, request, *args, **kwargs):
        data = cache.get('parks')
        if data is None:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            cache.set('parks',data,3600)
        return Response(data)

    @detail_route(methods=['get'])
    def price_history(self, request, format='json', pk=None):
        http_status = status.HTTP_200_OK
        try:
            price_history = ParkEntryRate.objects.all().order_by('-period_start')
            serializer = ParkEntryRateSerializer(price_history,many=True,context={'request':request},method='get')
            res = serializer.data
        except Exception as e:
            res ={
                "Error": str(e)
            }


        return Response(res,status=http_status)

    @detail_route(methods=['get'])
    def current_price(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            start_date = request.GET.get('arrival',False)
            res = []
            if start_date:
                start_date = datetime.strptime(start_date,"%Y-%m-%d").date()
                price_history = ParkEntryRate.objects.filter(period_start__lte = start_date).order_by('-period_start')
                if price_history:
                    serializer = ParkEntryRateSerializer(price_history,many=True,context={'request':request})
                    res = serializer.data[0]

        except Exception as e:
            res ={
                "Error": str(e)
            }
        return Response(res,status=http_status)

class FeatureViewSet(viewsets.ModelViewSet):
    queryset = Feature.objects.all()
    serializer_class = FeatureSerializer

class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer

class CampsiteClassViewSet(viewsets.ModelViewSet):
    queryset = CampsiteClass.objects.all()
    serializer_class = CampsiteClassSerializer

    def list(self, request, *args, **kwargs):
        active_only = bool(request.GET.get('active_only',False))
        if active_only:
            queryset = CampsiteClass.objects.filter(deleted=False)
        else:
            queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True,method='get')
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance,method='get')
        return Response(serializer.data)


    @detail_route(methods=['get'])
    def price_history(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            price_history = CampsiteClassPriceHistory.objects.filter(id=self.get_object().id).order_by('-date_start')
            # Format list
            open_ranges,formatted_list,fixed_list= [],[],[]
            for p in price_history:
                if p.date_end == None:
                    open_ranges.append(p)
                else:
                    formatted_list.append(p)

            for outer in open_ranges:
                for inner in open_ranges:
                    if inner.date_start > outer.date_start and inner.rate_id == outer.rate_id:
                        open_ranges.remove(inner)

            fixed_list = formatted_list + open_ranges
            fixed_list.sort(key=lambda x: x.date_start)
            serializer = CampsiteClassPriceHistorySerializer(fixed_list,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'],)
    def addPrice(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            rate = None
            serializer = RateDetailSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            rate_id = serializer.validated_data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=serializer.validated_data['adult'],concession=serializer.validated_data['concession'],child=serializer.validated_data['child'],infant=serializer.validated_data['infant'])[0]
            if rate:
                serializer.validated_data['rate']= rate
                data = {
                    'rate': rate,
                    'date_start': serializer.validated_data['period_start'],
                    'reason': PriceReason.objects.get(pk=serializer.validated_data['reason']),
                    'details': serializer.validated_data['details'],
                    'update_level': 1
                }
                self.get_object().createCampsitePriceHistory(data)
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id)
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'],)
    def updatePrice(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            original_data = request.data.pop('original')

            original_serializer = CampgroundPriceHistorySerializer(data=original_data)
            original_serializer.is_valid(raise_exception=True)

            serializer = RateDetailSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            rate_id = serializer.validated_data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=serializer.validated_data['adult'],concession=serializer.validated_data['concession'],child=serializer.validated_data['child'],infant=serializer.validated_data['infant'])[0]
            if rate:
                serializer.validated_data['rate']= rate
                new_data = {
                    'rate': rate,
                    'date_start': serializer.validated_data['period_start'],
                    'reason': PriceReason.objects.get(pk=serializer.validated_data['reason']),
                    'details': serializer.validated_data['details'],
                    'update_level': 1
                }
                self.get_object().updatePriceHistory(dict(original_serializer.validated_data),new_data)
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id)
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    @detail_route(methods=['post'],)
    def deletePrice(self, request, format='json', pk=None):
        try:
            http_status = status.HTTP_200_OK
            serializer = CampgroundPriceHistorySerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            self.get_object().deletePriceHistory(serializer.validated_data)
            price_history = CampgroundPriceHistory.objects.filter(id=self.get_object().id)
            serializer = CampgroundPriceHistorySerializer(price_history,many=True,context={'request':request})
            res = serializer.data

            return Response(res,status=http_status)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def list(self, request, *args, **kwargs):
        from django.db import connection, transaction
        search = request.GET.get('search[value]')
        draw = request.GET.get('draw') if request.GET.get('draw') else 1
        start = request.GET.get('start') if request.GET.get('draw') else 1
        length = request.GET.get('length') if request.GET.get('draw') else 10
        arrival = request.GET.get('arrival')
        departure= request.GET.get('departure')
        campground = request.GET.get('campground')
        region = request.GET.get('region')

        sql = ''
        http_status = status.HTTP_200_OK
        sqlSelect = 'select parkstay_booking.id as id, parkstay_campground.name as campground_name,parkstay_region.name as campground_region,parkstay_booking.legacy_name,\
            parkstay_booking.legacy_id,parkstay_campground.site_type as campground_site_type,\
            parkstay_booking.arrival as arrival, parkstay_booking.departure as departure,parkstay_campground.id as campground_id,parkstay_booking.invoice_reference'
        sqlCount = 'select count(*)'

        sqlFrom = ' from parkstay_booking\
            join parkstay_campground on parkstay_campground.id = parkstay_booking.campground_id\
            join parkstay_park on parkstay_campground.park_id = parkstay_park.id\
            join parkstay_district on parkstay_park.district_id = parkstay_district.id\
            join parkstay_region on parkstay_district.region_id = parkstay_region.id'

        sql = sqlSelect + sqlFrom + " where " if arrival or campground or region else sqlSelect + sqlFrom
        sqlCount = sqlCount + sqlFrom + " where " if arrival or campground or region else sqlCount + sqlFrom

        if campground :
            sqlCampground = ' parkstay_campground.id = {}'.format(campground)
            sql += sqlCampground
            sqlCount += sqlCampground
        if region:
            sqlRegion = " parkstay_region.id = {}".format(region)
            sql = sql+" and "+ sqlRegion if campground else sql + sqlRegion
            sqlCount = sqlCount +" and "+ sqlRegion if campground else sqlCount + sqlRegion
        if arrival:
            sqlArrival= ' parkstay_booking.arrival >= \'{}\''.format(arrival)
            sqlCount = sqlCount + " and "+ sqlArrival if campground or region else sqlCount + sqlArrival
            sql = sql + " and "+ sqlArrival if campground or region else sql + sqlArrival
            if departure:
                sql += ' and parkstay_booking.departure <= \'{}\''.format(departure)
                sqlCount += ' and parkstay_booking.departure <= \'{}\''.format(departure)
        if search:
            sqlsearch = ' lower(parkstay_campground.name) LIKE lower(\'%{}%\')\
            or lower(parkstay_region.name) LIKE lower(\'%{}%\')\
            or lower(parkstay_booking.legacy_name) LIKE lower(\'%{}%\')'.format(search,search,search)
            if arrival or campground or region:
                sql += " and ( "+ sqlsearch +" )"
                sqlCount +=  " and  ( "+ sqlsearch +" )"
            else:
                sql += ' where' + sqlsearch
                sqlCount += ' where ' + sqlsearch


        sql = sql + ' limit {} '.format(length)
        sql = sql + ' offset {} ;'.format(start)

        cursor = connection.cursor()
        cursor.execute("Select count(*) from parkstay_booking ");
        recordsTotal = cursor.fetchone()[0]
        cursor.execute(sqlCount);
        recordsFiltered = cursor.fetchone()[0]

        cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        data = [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]
        return Response(OrderedDict([
            ('recordsTotal', recordsTotal),
            ('recordsFiltered',recordsFiltered),
            ('results',data)
        ]),status=status.HTTP_200_OK)

    def create(self, request, format=None):
        from datetime import datetime
        try:
            start_date = datetime.strptime(request.data['arrival'],'%Y/%m/%d').date()
            end_date = datetime.strptime(request.data['departure'],'%Y/%m/%d').date()
            guests = request.data['guests']
            costs = request.data['costs']

            try:
                emailUser = request.data['customer']
                customer = EmailUser.objects.get(email = emailUser['email'])
            except EmailUser.DoesNotExist:
                raise
            booking_details = {
                'campsite_id':request.data['campsite'],
                'start_date' : start_date,
                'end_date' : end_date,
                'num_adult' : guests['adult'],
                'num_concession' : guests['concession'],
                'num_child' : guests['child'],
                'num_infant' : guests['infant'],
                'cost_total' : costs['total'],
                'customer' : customer
            }

            data = utils.internal_booking(request,customer,booking_details)
            serializer = BookingSerializer(data)
            return Response(serializer.data)
        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

class CampsiteRateViewSet(viewsets.ModelViewSet):
    queryset = CampsiteRate.objects.all()
    serializer_class = CampsiteRateSerializer

    def create(self, request, format=None):
        try:
            http_status = status.HTTP_200_OK
            rate = None
            print(request.data)
            rate_serializer = RateDetailSerializer(data=request.data)
            rate_serializer.is_valid(raise_exception=True)
            rate_id = rate_serializer.validated_data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=rate_serializer.validated_data['adult'],concession=rate_serializer.validated_data['concession'],child=rate_serializer.validated_data['child'])[0]
            print(rate_serializer.validated_data)
            if rate:
                data = {
                    'rate': rate.id,
                    'date_start': rate_serializer.validated_data['period_start'],
                    'campsite': rate_serializer.validated_data['campsite'],
                    'reason': rate_serializer.validated_data['reason'],
                    'update_level': 2
                }
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                res = serializer.save()

                serializer = CampsiteRateReadonlySerializer(res)
                return Response(serializer.data, status=http_status)

        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        try:
            http_status = status.HTTP_200_OK
            rate = None
            rate_serializer = RateDetailSerializer(data=request.data)
            rate_serializer.is_valid(raise_exception=True)
            rate_id = rate_serializer.validated_data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=rate_serializer.validated_data['adult'],concession=rate_serializer.validated_data['concession'],child=rate_serializer.validated_data['child'])[0]
                pass
            if rate:
                data = {
                    'rate': rate.id,
                    'date_start': rate_serializer.validated_data['period_start'],
                    'campsite': rate_serializer.validated_data['campsite'],
                    'reason': rate_serializer.validated_data['reason'],
                    'update_level': 2
                }
                instance = self.get_object()
                partial = kwargs.pop('partial', False)
                serializer = self.get_serializer(instance,data=data,partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)

                return Response(serializer.data, status=http_status)

        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

class BookingRangeViewset(viewsets.ModelViewSet):

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        original = bool(request.GET.get("original", False))
        serializer = self.get_serializer(instance, original=original, method='get')
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(instance,data=request.data,partial=partial)
            serializer.is_valid(raise_exception=True)
            if instance.range_end and not serializer.validated_data.get('range_end'):
                instance.range_end = None
            self.perform_update(serializer)

            return Response(serializer.data)
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(str(e))

class CampgroundBookingRangeViewset(BookingRangeViewset):
    queryset = CampgroundBookingRange.objects.all()
    serializer_class = CampgroundBookingRangeSerializer

class CampsiteBookingRangeViewset(BookingRangeViewset):
    queryset = CampsiteBookingRange.objects.all()
    serializer_class = CampsiteBookingRangeSerializer

class RateViewset(viewsets.ModelViewSet):
    queryset = Rate.objects.all()
    serializer_class = RateSerializer

# Reasons
# =========================
class ClosureReasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ClosureReason.objects.all()
    serializer_class = ClosureReasonSerializer

class OpenReasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OpenReason.objects.all()
    serializer_class = OpenReasonSerializer

class PriceReasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PriceReason.objects.all()
    serializer_class = PriceReasonSerializer

class MaximumStayReasonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MaximumStayReason.objects.all()
    serializer_class = MaximumStayReasonSerializer

class UsersViewSet(viewsets.ModelViewSet):
    queryset = EmailUser.objects.all()
    serializer_class = UsersSerializer

    def list(self, request, *args, **kwargs):
        start = request.GET.get('start') if request.GET.get('draw') else 1
        length = request.GET.get('length') if request.GET.get('draw') else 10
        q = request.GET.get('q')
        if q :
            queryset = EmailUser.objects.filter(email__icontains=q)[:10]
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset,many=True)
        return Response(serializer.data)
# Bulk Pricing
# ===========================
class BulkPricingView(generics.CreateAPIView):
    serializer_class = BulkPricingSerializer
    renderer_classes = (JSONRenderer,)

    def create(self, request,*args, **kwargs):
        try:
            http_status = status.HTTP_200_OK
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            print(serializer.validated_data)

            rate_id = serializer.data.get('rate',None)
            if rate_id:
                try:
                    rate = Rate.objects.get(id=rate_id)
                except Rate.DoesNotExist as e :
                    raise serializers.ValidationError('The selected rate does not exist')
            else:
                rate = Rate.objects.get_or_create(adult=serializer.validated_data['adult'],concession=serializer.validated_data['concession'],child=serializer.validated_data['child'])[0]
            if rate:
                data = {
                    'rate': rate,
                    'date_start': serializer.validated_data['period_start'],
                    'reason': PriceReason.objects.get(pk=serializer.data['reason']),
                    'details': serializer.validated_data['details']
                }
            if serializer.data['type'] == 'Park':
                for c in serializer.data['campgrounds']:
                    data['update_level'] = 0
                    Campground.objects.get(pk=c).createCampsitePriceHistory(data)
            elif serializer.data['type'] == 'Campsite Type':
                data['update_level'] = 1
                CampsiteClass.objects.get(pk=serializer.data['campsiteType']).createCampsitePriceHistory(data)

            return Response(serializer.data, status=http_status)

        except serializers.ValidationError:
            print(traceback.print_exc())
            raise
        except Exception as e:
            print(traceback.print_exc())
            raise serializers.ValidationError(str(e))
